/**
 * SlackAgentBot — A lightweight Slack channel for a dedicated agent bot.
 *
 * Each agent gets its own Slack app (separate bot token + app token) so it
 * appears as a real, @-mentionable bot in Slack with DM support.
 *
 * Unlike SlackChannel (the main bot), SlackAgentBot:
 * - Does NOT self-register via the channel factory
 * - Does NOT need sendMessageAs (the bot IS the identity)
 * - Does NOT sync all channel metadata
 * - Is created dynamically at startup from registered groups that have
 *   slackBotToken/slackAppToken in their containerConfig
 *
 * JID format: slackbot:{BOT_USER_ID}
 * All messages (from any channel or DM) are stored under this single JID.
 * Replies go to the channel where the most recent message was received.
 */

import { App, LogLevel } from '@slack/bolt';

import { ASSISTANT_NAME } from '../config.js';
import { logger } from '../logger.js';
import {
  Channel,
  OnInboundMessage,
  OnChatMetadata,
  RegisteredGroup,
} from '../types.js';
import { MAX_MESSAGE_LENGTH } from './slack.js';

export interface SlackAgentBotOpts {
  botToken: string;
  appToken: string;
  groupName: string; // Display name (e.g., "Bug Reporter")
  trigger: string; // Trigger pattern from registered group (e.g., "@BugReporter")
  onMessage: OnInboundMessage;
  onChatMetadata: OnChatMetadata;
  registeredGroups: () => Record<string, RegisteredGroup>;
}

export class SlackAgentBot implements Channel {
  name: string;

  private app: App;
  private botUserId: string | undefined;
  private connected = false;
  private outgoingQueue: Array<{ channelId: string; text: string }> = [];
  private lastReplyChannelId: string | undefined;
  private userNameCache = new Map<string, string>();

  private opts: SlackAgentBotOpts;

  constructor(opts: SlackAgentBotOpts) {
    this.opts = opts;
    this.name = `slack-agent:${opts.groupName}`;

    this.app = new App({
      token: opts.botToken,
      appToken: opts.appToken,
      socketMode: true,
      logLevel: LogLevel.ERROR,
    });

    this.setupEventHandlers();
  }

  /** The JID this bot owns: slackbot:{BOT_USER_ID} */
  get jid(): string {
    return this.botUserId ? `slackbot:${this.botUserId}` : '';
  }

  private setupEventHandlers(): void {
    // Handle @mentions in channels
    this.app.event('app_mention', async ({ event }) => {
      if (!event.text || !this.botUserId) return;
      await this.handleIncoming(
        event.channel,
        event.text,
        event.user || '',
        event.ts,
        true, // app_mention events are always in channels/groups
      );
    });

    // Handle DMs — Slack delivers DMs as message events with channel_type 'im'
    this.app.event('message', async ({ event }) => {
      const subtype = (event as { subtype?: string }).subtype;
      if (subtype && subtype !== 'bot_message') return;

      const msg = event as {
        text?: string;
        channel: string;
        channel_type?: string;
        user?: string;
        bot_id?: string;
        ts: string;
      };
      if (!msg.text) return;

      // Skip non-DM messages (those are handled by app_mention)
      if (msg.channel_type !== 'im') return;

      // Skip bot's own messages
      const isBotMessage = !!msg.bot_id || msg.user === this.botUserId;
      if (isBotMessage) return;

      await this.handleIncoming(
        msg.channel,
        msg.text,
        msg.user || '',
        msg.ts,
        false,
      );
    });
  }

  private async handleIncoming(
    channelId: string,
    text: string,
    userId: string,
    ts: string,
    isGroup: boolean,
  ): Promise<void> {
    if (!this.botUserId) return;

    const jid = `slackbot:${this.botUserId}`;
    const timestamp = new Date(parseFloat(ts) * 1000).toISOString();

    // Track reply channel so sendMessage knows where to post
    this.lastReplyChannelId = channelId;

    this.opts.onChatMetadata(jid, timestamp, undefined, 'slack', isGroup);

    const senderName = userId
      ? (await this.resolveUserName(userId)) || userId
      : 'unknown';

    // Translate <@BOT_USER_ID> mentions into the trigger pattern
    // so the trigger regex in the message loop matches
    let content = text;
    const mentionPattern = `<@${this.botUserId}>`;
    if (content.includes(mentionPattern)) {
      content = `${this.opts.trigger} ${content.replace(mentionPattern, '').trim()}`;
    }

    this.opts.onMessage(jid, {
      id: ts,
      chat_jid: jid,
      sender: userId,
      sender_name: senderName,
      content,
      timestamp,
      is_from_me: false,
      is_bot_message: false,
    });
  }

  async connect(): Promise<void> {
    await this.app.start();

    try {
      const auth = await this.app.client.auth.test();
      this.botUserId = auth.user_id as string;
      logger.info(
        { botUserId: this.botUserId, name: this.opts.groupName },
        'Slack agent bot connected',
      );
    } catch (err) {
      logger.warn(
        { name: this.opts.groupName, err },
        'Slack agent bot connected but failed to get bot user ID',
      );
    }

    this.connected = true;
    await this.flushOutgoingQueue();
  }

  async sendMessage(jid: string, text: string): Promise<void> {
    const channelId = this.lastReplyChannelId;

    if (!channelId || !this.connected) {
      if (channelId) {
        this.outgoingQueue.push({ channelId, text });
      }
      logger.info(
        { jid, name: this.opts.groupName },
        'Slack agent bot: no reply channel or disconnected, message queued',
      );
      return;
    }

    try {
      if (text.length <= MAX_MESSAGE_LENGTH) {
        await this.app.client.chat.postMessage({ channel: channelId, text });
      } else {
        for (let i = 0; i < text.length; i += MAX_MESSAGE_LENGTH) {
          await this.app.client.chat.postMessage({
            channel: channelId,
            text: text.slice(i, i + MAX_MESSAGE_LENGTH),
          });
        }
      }
      logger.info(
        { jid, channelId, name: this.opts.groupName, length: text.length },
        'Slack agent bot message sent',
      );
    } catch (err) {
      this.outgoingQueue.push({ channelId, text });
      logger.warn(
        { jid, channelId, name: this.opts.groupName, err },
        'Failed to send Slack agent bot message, queued',
      );
    }
  }

  isConnected(): boolean {
    return this.connected;
  }

  ownsJid(jid: string): boolean {
    return !!this.botUserId && jid === `slackbot:${this.botUserId}`;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    await this.app.stop();
  }

  async setTyping(_jid: string, _isTyping: boolean): Promise<void> {
    // no-op: Slack Bot API has no typing indicator endpoint
  }

  private async resolveUserName(userId: string): Promise<string | undefined> {
    if (!userId) return undefined;

    const cached = this.userNameCache.get(userId);
    if (cached) return cached;

    try {
      const result = await this.app.client.users.info({ user: userId });
      const name = result.user?.real_name || result.user?.name;
      if (name) this.userNameCache.set(userId, name);
      return name;
    } catch (err) {
      logger.debug({ userId, err }, 'Failed to resolve Slack user name');
      return undefined;
    }
  }

  private async flushOutgoingQueue(): Promise<void> {
    while (this.outgoingQueue.length > 0) {
      const item = this.outgoingQueue.shift()!;
      try {
        await this.app.client.chat.postMessage({
          channel: item.channelId,
          text: item.text,
        });
      } catch (err) {
        logger.warn(
          { channelId: item.channelId, err },
          'Failed to flush queued agent bot message',
        );
      }
    }
  }
}

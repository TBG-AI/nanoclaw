# TBG Mobile App - Comprehensive Mobile Features Documentation

**Repository:** Frontend/apps/mobile
**Platform:** React Native + Expo
**Last Updated:** 2026-03-03

---

## Table of Contents

1. [Push Notification Implementation](#1-push-notification-implementation)
2. [Deep Linking System](#2-deep-linking-system)
3. [Native Module Integrations](#3-native-module-integrations)
4. [Navigation Patterns](#4-navigation-patterns)
5. [Offline Capabilities](#5-offline-capabilities)
6. [Platform-Specific Code](#6-platform-specific-code)
7. [Expo Configuration](#7-expo-configuration)
8. [App Store Metadata](#8-app-store-metadata)
9. [Crash Reporting & Analytics](#9-crash-reporting--analytics)
10. [Background Task Handling](#10-background-task-handling)

---

## 1. Push Notification Implementation

### Overview
The app uses **Expo Notifications** with **Firebase Cloud Messaging (FCM)** for production push notifications.

### Key Files
- `/packages/mobile-core/src/notifications/handlers/notificationHandler.ts` - Main notification handler
- `/packages/mobile-core/src/notifications/config/channels.ts` - Android notification channels
- `/apps/mobile/src/hooks/useAppBootstrap.ts` - Push token registration

### Implementation Details

#### Notification Handler Hook (`useNotificationHandler`)
```typescript
Location: packages/mobile-core/src/notifications/handlers/notificationHandler.ts

Features:
- Android notification channels setup
- Notification tap listeners (foreground/background)
- Cold start notification handling
- Deep link generation from notification data
- Analytics tracking (PostHog)
```

#### Android Notification Channels
Configured in `NOTIFICATION_CHANNELS` array with properties:
- Channel ID and name
- Importance level (HIGH, MAX, DEFAULT)
- Vibration patterns
- Light color
- Sound settings
- Badge settings

#### Push Token Registration
**Location:** `useAppBootstrap.ts`

**Token Sync Strategy:**
1. **On login:** Automatic sync via `globalUserStore.setGlobalUser()`
2. **On app foreground:** `AppState` listener calls `registerPushToken()`
3. **Purpose:** Ensures backend always has latest FCM token for admin notifications

#### Notification Processing Flow
1. **Cold Start:** App opened by tapping notification
   - `getLastNotificationResponseAsync()` retrieves notification
   - Deduplication via `processedNotificationIds` Set
   - Process notification → generate deep link → navigate

2. **Foreground/Background:** App running when notification tapped
   - `addNotificationResponseReceivedListener` handles tap
   - Extract notification data (event_type, event_id, etc.)
   - Generate deep link using `getDeepLinkForNotification()`
   - Track tap event in PostHog

#### Deep Link Generation from Notifications
```typescript
const { path: deepLinkPath, source: deepLinkSource } = getDeepLinkForNotification(data);
const fullDeepLink = buildFullDeeplink(deepLinkPath, appScheme);
handleAnyDeepLink(fullDeepLink);
```

#### Configuration
**Expo Config (`app.config.js`):**
```javascript
["expo-notifications", {
  mode: "production",              // Use FCM
  iosDisplayInForeground: true,    // Show notifications in foreground
  icon: validNotificationIcon,     // Custom Android icon
}]
```

**Android Manifest:**
```xml
<meta-data android:name="com.google.firebase.messaging.default_notification_icon"
           android:resource="@drawable/notification_icon"/>
```

---

## 2. Deep Linking System

### Overview
Sophisticated deep linking system supporting:
- **Universal Links (iOS)** - `applinks:thebeautifulgame.live`
- **App Links (Android)** - Auto-verified with `android:autoVerify="true"`
- **Custom URL Schemes** - `tbg://`, `tbg-ab://`, `tbg-slough://`
- **AppsFlyer OneLink** - Attribution deep links
- **Referral Links** - User invite system

### Key Files
- `/apps/mobile/src/hooks/useDeepLinkHandler.ts` - Main deep link handler
- `/apps/mobile/src/utils/appsflyer/deepLinkProcessing.ts` - AppsFlyer deep link processing (2169 lines!)
- `/packages/mobile-core/src/notifications/deeplinks/` - Deep link registry and generation
- `/apps/mobile/ios/TBGdev2/AppDelegate.swift` - iOS native deep link handling
- `/apps/mobile/android/app/src/main/AndroidManifest.xml` - Android intent filters

### Universal Links (iOS)

#### Configuration
**Associated Domains (`app.config.js`):**
```javascript
associatedDomains: [
  "applinks:thebeautifulgame.live",
  "applinks:www.thebeautifulgame.live",
  "applinks:thebeautifulgame.global",
  "applinks:www.thebeautifulgame.global",
]
```

**iOS Native Handler (`AppDelegate.swift`):**
```swift
public override func application(
  _ application: UIApplication,
  continue userActivity: NSUserActivity,
  restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
) -> Bool {
  AppsFlyerAttribution.shared().continue(userActivity, restorationHandler: nil)
  let result = RCTLinkingManager.application(application, continue: userActivity,
                                            restorationHandler: restorationHandler)
  return super.application(application, continue: userActivity,
                          restorationHandler: restorationHandler) || result
}
```

### App Links (Android)

#### Intent Filters
**Auto-verified App Links:**
```xml
<intent-filter android:autoVerify="true">
  <action android:name="android.intent.action.VIEW"/>
  <data android:scheme="https" android:host="www.thebeautifulgame.live"
        android:pathPrefix="/history"/>
  <data android:pathPrefix="/picks"/>
  <data android:pathPrefix="/promos"/>
  <data android:pathPrefix="/store"/>
  <data android:pathPrefix="/tournaments"/>
  <data android:pathPrefix="/referral"/>
  <category android:name="android.intent.category.BROWSABLE"/>
  <category android:name="android.intent.category.DEFAULT"/>
</intent-filter>
```

**AppsFlyer OneLink:**
```xml
<intent-filter android:autoVerify="true">
  <data android:scheme="https" android:host="tbg-picks.onelink.me"/>
</intent-filter>
```

**Important Note:** `/payment` path is intentionally excluded - must open in Chrome Custom Tabs for Google Pay compatibility.

### Custom URL Schemes

**Configured Schemes:**
- `tbg://` - Main TBG brand
- `tbg-ab://` - Alternative brand
- `tbg-slough://` - Slough Town brand
- `exp+tbg://` - Expo development scheme
- Facebook deep linking: `fb1900934827479981://`
- Google OAuth: `com.googleusercontent.apps.{CLIENT_ID}://`

### Deep Link Handler Hook

**Location:** `apps/mobile/src/hooks/useDeepLinkHandler.ts`

**Flow:**
1. **Warm Start:** App running, user taps link → `Linking.addEventListener('url')`
2. **Cold Start:** App opened from link → `Linking.getInitialURL()`
3. Both paths call `handleAnyDeepLink(url, { source })`

### AppsFlyer Deep Link Processing

**Location:** `apps/mobile/src/utils/appsflyer/deepLinkProcessing.ts`

This is the most complex module in the mobile app (2169 lines). Key features:

#### Permission-Gated Processing
Deep link processing is queued until required permissions are granted:

**Permission Hierarchy:**
1. **Location Permission** (first) - Required for all platforms
2. **ATT Permission** (second, iOS only) - For IDFA matching

**Queue System:**
- In-memory queue + persistent AsyncStorage
- Auto-cleanup after 3 days (5 min in dev)
- Max 3 retry attempts on error
- Realtime expiration timer

#### Key Functions

**`processDeepLinkResponse()`**
- Main entry point from AppsFlyer `onDeepLink` callback
- Checks permissions in hierarchy
- Queues if permissions not ready
- Processes immediately if ready

**`queueDeepLinkUntilPermissionsResolve()`**
- Stores deep link in memory and AsyncStorage
- Schedules expiration cleanup timer
- Tracks error count and timestamps

**`processQueuedDeepLinkWithPermissionGate()`**
- Unified processing function
- Checks permissions first (gate)
- Loads from memory or storage
- Processes when ready
- Cleans up on success

**`arePermissionsResolved()`**
- Checks if both location and ATT are ready
- iOS: Location granted + ATT determined
- Android: Location granted only

#### Deep Link Types

**1. Referral Links**
```typescript
deep_link_value: "referral"
deep_link_sub1: "ABC123"  // Referral code
```

**2. Re-engagement Links**
```typescript
deep_link_value: "/picks"
media_source: "facebook"
campaign: "retargeting"
```

**3. Deferred Deep Links**
- Processed on first app open after install
- Queued if ATT not determined (iOS)
- Maximizes IDFA matching

#### Analytics Integration
Tracks deep link events to PostHog:
- `appsflyer_deeplink_received` - Successful processing
- `appsflyer_deeplink_queued_for_permissions` - Queued for permissions
- `appsflyer_deeplink_processed_with_permission_gate` - Processed from queue
- `appsflyer_deeplink_not_found` - Link not found
- `appsflyer_deeplink_error` - Processing error

### Deep Link Testing Utilities

**Dev-Only Tools:**
- `deepLinkTestUtils.ts` - Manual deep link injection
- `deepLinkDevServer.ts` - WebSocket server for remote triggering
- Scripts: `deeplink:inspect`, `deeplink:log`, `deeplink:cleanup`, `deeplink:health`

---

## 3. Native Module Integrations

### Overview
The app integrates various native modules through Expo and React Native libraries.

### Camera & Photo Library

**Module:** `expo-image-picker`

**Configuration (`app.config.js`):**
```javascript
["expo-image-picker", {
  photosPermission: "The app accesses your photos to set your profile picture.",
  cameraPermission: false,  // Disabled - photo library only
}]
```

**Usage:** Profile picture selection from photo library only (no camera capture).

### Location Services

**Module:** `expo-location`

**Permissions:**
- iOS: `NSLocationWhenInUseUsageDescription`
- Android: `ACCESS_COARSE_LOCATION`, `ACCESS_FINE_LOCATION`

**Purpose:** Geo-restriction enforcement - verify app availability in user's location.

**Implementation:**
- `LocationManager` component in `packages/mobile-core/components/location`
- Persistent location checking for all users
- Required for deep link processing (permission gate)

### Biometrics

**Not Currently Implemented**

The app does not use biometric authentication (Face ID, Touch ID, fingerprint). Authentication is handled via:
- Email/password
- Google Sign-In (`@react-native-google-signin/google-signin`)
- Apple Sign-In (`expo-apple-authentication`)

### Native Modules List

**Authentication:**
- `expo-apple-authentication` - Apple Sign-In
- `@react-native-google-signin/google-signin` - Google OAuth

**Media:**
- `expo-image-picker` - Photo library access
- `expo-av` - Audio/video playback (no recording)
- `expo-video` - Video playback
- `expo-image` - Optimized image rendering

**Device:**
- `expo-application` - App version, build info
- `expo-device` - Device model, OS version
- `expo-location` - Geolocation

**Storage:**
- `expo-secure-store` - Secure key-value storage (auth tokens)
- `@react-native-async-storage/async-storage` - Persistent storage
- `expo-file-system` - File operations

**Other:**
- `expo-clipboard` - Copy/paste
- `expo-web-browser` - In-app browser
- `expo-store-review` - Native app rating prompt
- `react-native-share` - System share sheet
- `react-native-qrcode-svg` - QR code generation

### In-App Purchases

**Module:** `react-native-iap`

**Platform Support:**
- iOS: StoreKit
- Android: Google Play Billing

**Permission:** `com.android.vending.BILLING`

---

## 4. Navigation Patterns

### Overview
Custom navigation system (not React Navigation) using context-based state management.

### Key Files
- `/packages/mobile-core/navigation/NavigationContext.tsx` - Navigation state and methods
- `/packages/mobile-core/navigation/BottomNavigationTabs.tsx` - Bottom tab bar
- `/apps/mobile/src/AppShell.tsx` - Main app structure

### Navigation Context

**Provider:** `NavigationProvider`

**State:**
```typescript
{
  currentPage: 'home' | 'tournaments' | 'history' | 'promos' | 'store' | 'onboarding' | 'webpayment',
  previousPage: MainPage | null,
  currentHomePage: 'picks' | 'live' | 'crafter',
  profileSheetOpen: boolean
}
```

**Methods:**
- `setCurrentPage(page)` - Navigate to main page
- `setCurrentHomePage(page)` - Switch home tabs
- `openProfileSheet()` / `closeProfileSheet()` - Profile bottom sheet
- `navigateBack()` - Return to previous page

### Page Structure

**Main Pages (with bottom nav):**
1. **Home** - Multi-tab (Picks, Live, Crafter)
2. **Tournaments** - Tournament listings
3. **History** - Bet history
4. **Promos** - Promotions
5. **Store** - In-app purchases

**Special Pages (no bottom nav):**
- **Onboarding** - First-time user flow (unauthenticated state)
- **WebPayment** - Payment flow (purchase/withdrawal)

### Bottom Navigation

**Component:** `BottomNavigationTabs`

**Behavior:**
- Hidden on Crafter page (has its own betslip bar)
- Hidden on Onboarding page
- Fixed position at bottom with z-index elevation
- Brand-aware icons and colors

### Deep Link Navigation

Deep links trigger navigation via `handleAnyDeepLink()`:
1. Parse URL (e.g., `tbg://picks`)
2. Extract page and parameters
3. Call `setCurrentPage(page)`
4. Handle special cases (referral → auth modal)

### Force Authentication

**Location:** `AppShell.tsx`

**Flow:**
1. Check `globalUser?.user_id`
2. If not authenticated → route to onboarding
3. Prevent access to main app until authenticated
4. Auto-complete onboarding after successful auth

---

## 5. Offline Capabilities

### Overview
The app has **limited offline support**. Most features require network connectivity.

### Offline-Capable Features

**1. Cached Data Display**
- User profile data (in memory via Zustand)
- Previously loaded picks/matches
- App configuration (themes, i18n)

**2. Persistent Storage**
- AsyncStorage for:
  - Auth tokens (Secure Store)
  - Attribution data
  - Queued deep links
  - App preferences
  - Changelog tracking

**3. Asset Caching**
- Bundled fonts
- App icons and splash screens
- Brand assets (via Expo asset bundling)

### Network-Required Features

**The following require active connection:**
- Authentication (login/signup)
- Fetching picks and live scores
- Placing bets
- In-app purchases
- Notifications
- Profile updates
- Payment operations

### Sync Mechanism

**No background sync** - The app does not queue offline actions for later sync.

**On app foreground:**
1. Fetch latest user data (`fetchUserData()`)
2. Sync push token
3. Process queued deep links
4. Check for app updates

### Error Handling

**Network errors:**
- Display toast notifications
- Retry logic in API layer (via React Query)
- Fallback to cached data where applicable

---

## 6. Platform-Specific Code

### Overview
Platform-specific implementations for iOS and Android.

### File Structure

**iOS:**
```
apps/mobile/ios/
├── TBGdev2/
│   ├── AppDelegate.swift          # App lifecycle, deep links
│   ├── Info.plist                 # iOS configuration
│   ├── TBGdev2.entitlements       # App capabilities
│   ├── GoogleService-Info.plist   # Firebase config
│   └── Images.xcassets/           # App icons, splash screens
└── Podfile                        # CocoaPods dependencies
```

**Android:**
```
apps/mobile/android/
├── app/src/main/
│   ├── java/com/tbg/main/dev2/
│   │   ├── MainActivity.kt        # Main activity
│   │   └── MainApplication.kt     # Application setup
│   ├── AndroidManifest.xml        # Android configuration
│   └── res/                       # Resources, icons
└── build.gradle                   # Build configuration
```

### iOS-Specific Features

#### AppDelegate.swift
```swift
Responsibilities:
- Firebase initialization: FirebaseApp.configure()
- Deep link handling: AppsFlyer + RCTLinkingManager
- Universal Links: continue userActivity
- Custom URL schemes: handleOpen
```

#### Info.plist Key Configurations
```xml
Key Settings:
- CFBundleURLTypes: URL schemes (tbg://, Google OAuth, Facebook)
- Associated domains: Universal Links
- SKAdNetworkItems: 47 Google SKAdNetwork IDs for iOS attribution
- NSLocationWhenInUseUsageDescription: Location permission reason
- NSUserTrackingUsageDescription: ATT permission reason
- GADApplicationIdentifier: Google Ads app ID
- FacebookAppID: Facebook SDK integration
```

#### Entitlements
```xml
TBGdev2.entitlements:
- Associated Domains (Universal Links)
- Push Notifications
```

### Android-Specific Features

#### MainActivity.kt
```kotlin
Responsibilities:
- Splash screen setup (SplashScreenManager)
- Back button behavior (moveTaskToBack for root activities)
- React Native bridge setup
- New Architecture support
```

#### MainApplication.kt
```kotlin
Responsibilities:
- SoLoader initialization
- React Native host configuration
- Expo module lifecycle
- New Architecture loading
```

#### AndroidManifest.xml Key Configurations
```xml
Key Settings:
- Permissions: Location, Internet, Billing, AD_ID
- Removed permissions: CAMERA, FOREGROUND_SERVICE (explicitly removed)
- Intent filters: App Links (autoVerify), URL schemes
- Meta-data: Google Ads, Firebase, Analytics consent defaults
```

### Platform Checks in Code

**Usage Pattern:**
```typescript
import { Platform } from 'react-native';

if (Platform.OS === 'ios') {
  // iOS-specific code
} else if (Platform.OS === 'android') {
  // Android-specific code
}
```

**Common Platform Checks:**
- ATT permission (iOS only)
- Notification channels (Android only)
- Deep link processing differences
- Attribution configuration

### Platform-Specific Modules

**iOS Only:**
- `expo-apple-authentication` - Apple Sign-In
- ATT permission handling

**Android Only:**
- Notification channels setup
- Intent filter handling

---

## 7. Expo Configuration

### Overview
The app uses **Expo SDK 53** with custom native code and EAS Build.

### Key Configuration Files

**1. app.config.js** (12,657 bytes)
- Dynamic configuration based on environment
- Brand-aware asset selection
- Platform-specific settings
- Plugin configuration

**2. eas.json**
```json
{
  "build": {
    "base": {
      "node": "20.19.4",
      "pnpm": "10.13.1"
    },
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal"
    },
    "production": {
      "autoIncrement": true
    }
  }
}
```

**3. babel.config.js**
- Module resolver for path aliases
- Expo preset

**4. metro.config.js**
- Monorepo workspace support
- Asset resolution

### Expo Plugins

**Custom Config Plugins:**

**1. withGoogleMobileAds.js**
- Configures GMA SDK for attribution-only mode
- Adds SKAdNetwork IDs (47 Google IDs)
- Sets consent mode defaults
- Delays app measurement until SDK init

**2. withFirebaseModularHeaders.js**
- Configures Firebase modular headers
- Ensures compatibility with v22 SDK

**3. withAttributionDependencies.js**
- Manages attribution SDK dependencies
- AppsFlyer configuration

**4. withEnvSync.js**
- Syncs environment variables to native projects
- Updates GoogleService-Info.plist and google-services.json

**5. withPermissionsHandler.js**
- Manages permission strings
- Adds/removes permissions based on config

### Expo Modules Used

**Core:**
- `expo` ~53.0.22
- `expo-dev-client` ~5.2.4
- `expo-constants` ~17.1.7
- `expo-splash-screen` ~0.30.10
- `expo-status-bar` ~2.2.3
- `expo-updates` (disabled in config)

**UI:**
- `expo-font` ~13.3.2
- `expo-image` ~2.4.1
- `expo-blur` ~14.1.5
- `expo-linear-gradient` ~14.1.5

**Device:**
- `expo-application` ~6.1.5
- `expo-device` ~7.1.4
- `expo-location` ~18.1.6
- `expo-notifications` ~0.31.4

**Storage:**
- `expo-secure-store` ~14.2.4
- `expo-file-system` ~18.1.11

**Media:**
- `expo-av` ~15.1.7
- `expo-video` ~2.2.2
- `expo-image-picker` ~16.1.4
- `expo-image-manipulator` ~14.0.8

**Auth:**
- `expo-apple-authentication` ~8.0.7
- `expo-auth-session` ~6.2.1
- `expo-web-browser` ~14.2.0

**Other:**
- `expo-clipboard` ~7.1.5
- `expo-crypto` ~14.1.5
- `expo-store-review` ~8.1.5
- `expo-gl` ~15.1.7 (for 3D rendering)
- `expo-three` ~8.0.0

### Build Configuration

**EAS Build:**
- Uses pnpm workspaces
- Supports multiple brands (TBG, AB, Slough)
- Environment-specific builds
- Auto-increment version codes

**Version Management:**
```javascript
VERSION: process.env.VERSION || "1.0.0"
ANDROID_VERSION_CODE: Number(process.env.ANDROID_VERSION_CODE || 1)
IOS_BUILD_NUMBER: process.env.IOS_BUILD_NUMBER || "1"
```

### New Architecture Support

**Enabled:**
```javascript
newArchEnabled: true
```

**Benefits:**
- Improved performance
- Better memory management
- Fabric renderer
- TurboModules

---

## 8. App Store Metadata

### Overview
Brand-aware app metadata and assets configured dynamically.

### App Identifiers

**Bundle IDs:**
```javascript
const ids = {
  tbg: {
    ios: "com.tbg.main",
    android: "com.tbg.main"
  },
  ab: {
    ios: "com.tbg.ab",
    android: "com.tbg.ab"
  },
  slough: {
    ios: "com.tbg.slough",
    android: "com.tbg.slough"
  }
};
```

**App Names:**
- TBG: "TBG"
- AB: "TBG-AB"
- Slough: "TBG-Slough"

### App Icons

**Location:** Brand-specific or shared
```javascript
const icon = pick(brandDir, sharedDir, "icon.png");
const adaptiveIcon = pick(brandDir, sharedDir, "adaptive-icon.png");
```

**Paths:**
- `packages/brands/{BRAND}/assets/icon.png`
- `packages/mobile-ui/assets/icon.png` (fallback)

**iOS:**
- `apps/mobile/ios/TBGdev2/Images.xcassets/AppIcon.appiconset/`
- Multiple sizes generated by Expo

**Android:**
- Adaptive icon with foreground + background
- Notification icon (monochrome)

### Splash Screens

**Configuration:**
```javascript
splash: {
  image: validIosSplash || validAndroidSplash,
  resizeMode: "cover",
  backgroundColor: "#000000",
}
```

**Custom Splash Video:**
- `SplashVideo` component in `@mobile-core/app/SplashVideo`
- Plays branded video before app content
- Overlays main app with z-index 10000

**Assets:**
- `ios-splash.png` / `android-splash.png` (brand-specific)
- `splash.png` (fallback)

### App Store Descriptions

**Not in code** - Managed manually in App Store Connect and Google Play Console.

**Typical Content:**
- App description
- Keywords
- Screenshots
- Privacy policy URL
- Support URL
- Age rating

### Versioning

**Current Version (from Info.plist):**
- Version: 1.3.7
- Build: 114

**Auto-increment:**
```json
"production": {
  "autoIncrement": true
}
```

### App Store Categories

**Not configured in code** - Set in store consoles:
- Likely: Games / Sports

---

## 9. Crash Reporting & Analytics

### Overview
Multi-SDK analytics and crash reporting setup.

### Crash Reporting

#### Firebase Crashlytics

**Module:** `@react-native-firebase/crashlytics`

**Configuration:**
- Initialized in AppDelegate.swift: `FirebaseApp.configure()`
- Automatic crash collection
- Non-fatal error reporting

**Usage:**
```typescript
import crashlytics from '@react-native-firebase/crashlytics';

crashlytics().recordError(error);
```

#### PostHog Exception Capture

**Module:** `posthog-react-native`

**Global Error Handler:**
```typescript
// In App.tsx
const handleGlobalError = (error: Error, isFatal: boolean) => {
  posthog.capture('$exception', {
    $exception_message: error.message,
    $exception_type: error.name,
    $exception_stack_trace_raw: error.stack,
    platform: 'mobile',
    isFatal,
  });
};

<FabricErrorProvider errorLogger={handleGlobalError}>
```

**Error Provider:**
- `FabricErrorProvider` wraps entire app
- Catches all JavaScript errors
- Reports to PostHog + console.error

### Analytics

#### PostHog

**Module:** `posthog-react-native` + `posthog-react-native-session-replay`

**Location:** `/packages/mobile-core/src/analytics/posthog.ts`

**Initialization:**
```typescript
export const posthog = new PostHog(
  ENV.POSTHOG_KEY,
  {
    host: ENV.POSTHOG_HOST,
    captureMode: 'form',
    sessionReplay: {
      maskAllTextInputs: true,
      maskAllImages: false,
    }
  }
);
```

**Features:**
- Event tracking
- User identification
- Session replay
- Feature flags

**Key Events:**
- `appsflyer_deeplink_received`
- `appsflyer_deeplink_queued_for_permissions`
- `att_permission_early_request`
- `app_install` / `app_reinstall`
- `notification_tapped`
- `payment_successful`

#### Firebase Analytics (GA4)

**Module:** `@react-native-firebase/analytics`

**Location:** `/packages/mobile-core/src/analytics/attribution.ts`

**Initialization:**
```typescript
import { getAnalytics, setUserId, logEvent } from '@react-native-firebase/analytics';
```

**Features:**
- Conversion tracking
- User properties
- Google Ads integration
- BigQuery export

**Consent Management:**
```typescript
// iOS: Reactive to ATT status
await setConsent(analyticsInstance, {
  ad_storage: attStatus === 'authorized',
  analytics_storage: true,
  ad_user_data: attStatus === 'authorized',
  ad_personalization: attStatus === 'authorized',
});

// Android: Silent attribution grant
await setConsent(analyticsInstance, {
  ad_storage: true,
  analytics_storage: true,
  ad_user_data: true,
  ad_personalization: true,
});
```

#### AppsFlyer

**Module:** `react-native-appsflyer`

**Location:** `/apps/mobile/src/hooks/useAttributionTracking.ts`

**Features:**
- Install attribution
- Deep link handling
- Re-engagement tracking
- OneLink support

**SDK Configuration:**
```typescript
appsFlyer.initSdk({
  devKey: ENV.APPSFLYER_DEV_KEY,
  appId,
  isDebug: __DEV__,
  onInstallConversionDataListener: true,
  onDeepLinkListener: true,
  timeToWaitForATTUserAuthorization: 30,
});
```

**Callbacks:**
- `onInstallConversionData` - Attribution data
- `onDeepLink` - Deep link events
- `onAppOpenAttribution` - Re-engagement

**Attribution Flow:**
1. GMA SDK initializes first (captures GBRAID/WBRAID)
2. AppsFlyer SDK initializes after GMA ready
3. Wait for ATT on iOS (30s timeout)
4. Send first_launch event
5. Process attribution data → PostHog + GA4

#### Google Mobile Ads (GMA) SDK

**Module:** `react-native-google-mobile-ads`

**Purpose:** Attribution-only (no ads displayed)

**Key Function:**
```typescript
// Location: apps/mobile/src/utils/gmaSDK.ts
export async function initializeGMASDK(): Promise<void> {
  await MobileAds().initialize();
  console.log('✅ [GMA] Initialized (attribution-only, no ads)');
}
```

**Captures:**
- GBRAID (Google Click ID for web-to-app)
- WBRAID (Apple Search Ads attribution)

### User Identification

**Unified Function:**
```typescript
// Location: packages/mobile-core/src/analytics/attribution.ts
export async function identifyUserForAttribution(user: UserIdentificationData) {
  // PostHog
  identifyPostHogUser(user_id, { email, username, phone_number });

  // AppsFlyer
  appsFlyer.setCustomerUserId(user_id);
  appsFlyer.setUserEmails({ emails: [normalizedEmail], emailsCryptType: 2 });

  // GA4
  await setUserId(analyticsInstance, user_id);
  await setUserProperties(analyticsInstance, { email, username });
}
```

**Called:**
- Before user_registered event
- On login
- On app foreground (if authenticated)

### Reactotron (Dev Only)

**Module:** `reactotron-react-native`

**Location:** `/apps/mobile/src/config/ReactotronConfig.ts`

**Features:**
- Redux state inspection (if used)
- Network request logging
- Console log capture
- Custom commands

---

## 10. Background Task Handling

### Overview
The app has **minimal background capabilities** by design.

### Explicitly Disabled Features

**Android Foreground Services:**
```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" tools:node="remove"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" tools:node="remove"/>
```

**Expo AV Configuration:**
```javascript
["expo-av", {
  microphonePermission: false,
  supportsBackgroundPlayback: false,  // Explicitly disabled
}]
```

**Reason:** Avoid FOREGROUND_SERVICE permission requirement, as app doesn't need background audio/video playback.

### Background Modes

**iOS UIBackgroundModes:**
```xml
<key>UIBackgroundModes</key>
<array/>  <!-- Empty - no background modes -->
```

**Not Enabled:**
- Background audio
- Background location updates
- Background fetch
- VoIP
- Background processing

### What Runs in Background

**1. Push Notifications**
- FCM handles delivery
- System wakes app when notification tapped
- No custom background handlers

**2. Attribution SDKs**
- AppsFlyer tracks session lifecycle
- Firebase Analytics tracks screen views
- Minimal background processing

**3. System Services**
- Network state changes
- App state transitions (active/inactive/background)

### App State Handling

**Location:** `apps/mobile/src/hooks/useAppStateHandler.ts`

**On App Foreground:**
1. Fetch latest user data
2. Sync push token
3. Process queued deep links
4. Check grouped permissions

**Implementation:**
```typescript
useEffect(() => {
  const subscription = AppState.addEventListener(
    'change',
    (nextAppState: AppStateStatus) => {
      if (
        appState.current.match(/inactive|background/) &&
        nextAppState === 'active'
      ) {
        fetchUserData();
        registerPushToken();
        processQueuedDeepLinkWithPermissionGate();
      }
      appState.current = nextAppState;
    }
  );
  return () => subscription.remove();
}, []);
```

### No Background Sync

The app does not implement:
- Background data sync
- Offline action queues
- Scheduled tasks
- Background downloads

**Philosophy:** Real-time app - require active connection for all operations.

---

## Additional Technical Details

### Monorepo Structure

The mobile app is part of a pnpm workspace monorepo:

```
Frontend/
├── apps/
│   └── mobile/              # This app
├── packages/
│   ├── mobile-core/         # Shared mobile components/logic
│   ├── mobile-ui/           # Shared UI components
│   ├── brands/              # Brand-specific assets
│   └── shared/              # Cross-platform shared code
```

### State Management

**Zustand Stores:**
- `useGlobalUserStore` - User data and auth state
- `useGlobalAuthModalStore` - Auth modal state
- `useGlobalOnboardingStore` - Onboarding flow state
- `useGlobalBannedUserStore` - Banned user state
- `useGlobalChangelogStore` - Changelog data
- `useGlobalUserBalanceUpdateStore` - Balance refresh trigger
- `useWebPaymentStore` - Payment flow state

**Location:** `packages/shared/stores/globalStores.ts`

### API Layer

**React Query:**
- `@tanstack/react-query` ~5.83.0
- Query caching
- Automatic retries
- Background refetching

**API Client:**
- Location: `packages/shared/api/`
- Axios-based
- Token management
- Error handling (401 → logout, 403 → banned modal)

### Internationalization

**Module:** `react-i18next` + `i18next`

**Supported Languages:**
- English (en)
- Spanish (es)
- Danish (da)

**Location:** `packages/mobile-core/src/locales/`

**Detection:**
- Device language (via `react-native-localize`)
- User preference (stored in backend)

### Security

**Token Storage:**
- Secure Store (iOS Keychain, Android Keystore)
- Never in plain AsyncStorage

**API Security:**
- Bearer token authentication
- HTTPS only
- Certificate pinning: Not implemented

**Deep Link Validation:**
- Referral code validation
- URL scheme verification
- Path prefix matching

### Performance Optimizations

**Image Optimization:**
- `expo-image` with caching
- Progressive loading
- WebP support

**Font Loading:**
- Custom fonts bundled
- Preloaded in bootstrap

**Code Splitting:**
- Dynamic imports for heavy modules
- Lazy loading for screens

**Memory Management:**
- Image cache limits
- Cleanup on unmount
- Deduplication (notification IDs, deep links)

---

## Summary

This mobile app is a **production-grade React Native + Expo application** with:

1. **Sophisticated deep linking** - Multi-source (Universal Links, App Links, AppsFlyer, Referrals) with permission-gated processing and persistent queue

2. **Comprehensive analytics** - PostHog, Firebase/GA4, AppsFlyer with unified user identification

3. **Push notifications** - FCM-based with channel management and deep link integration

4. **Attribution tracking** - GMA SDK + AppsFlyer + GA4 with consent management and IDFA/GAID capture

5. **Multi-brand support** - Dynamic configuration for TBG, AB, and Slough brands

6. **Platform-specific optimizations** - iOS Universal Links, Android App Links, SKAdNetwork, consent modes

7. **Production-ready error handling** - Firebase Crashlytics + PostHog exception capture + global error boundary

8. **Minimal background processing** - Focused on foreground experience with efficient app state handling

The codebase demonstrates advanced React Native patterns, comprehensive SDK integrations, and production-ready mobile development practices.

---

**End of Documentation**

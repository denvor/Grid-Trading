## ADDED Requirements

### Requirement: Theme toggle UI
The system SHALL display a theme toggle button in the navigation bar that cycles through three states: light, dark, and system.

#### Scenario: Toggle cycling
- **WHEN** user clicks the theme toggle button
- **THEN** system cycles to the next theme state (light → dark → system → light) and immediately applies it

#### Scenario: Default theme
- **WHEN** a new user visits the application for the first time
- **THEN** system defaults to dark theme

#### Scenario: System preference detection
- **WHEN** user selects "system" theme
- **THEN** system matches the OS preference via `prefers-color-scheme` media query

### Requirement: Theme persistence
The system SHALL persist the selected theme to `localStorage` and restore it on next visit.

#### Scenario: Persistence across sessions
- **WHEN** user selects "light" theme and refreshes the page
- **THEN** system restores "light" theme

#### Scenario: System theme re-evaluation
- **WHEN** user has "system" theme saved and OS preference changes
- **THEN** system reflects the new OS preference on next page load

### Requirement: Light theme styling
The system SHALL provide a complete light-theme stylesheet that meets WCAG AA contrast ratios.

#### Scenario: Light theme readability
- **WHEN** light theme is active
- **THEN** all text meets 4.5:1 contrast ratio against its background

#### Scenario: Component consistency
- **WHEN** light theme is active
- **THEN** Bootstrap components (cards, tables, buttons, badges) remain visually consistent

### Requirement: No flash of wrong theme
The system SHALL apply the saved theme before first paint to avoid flashing the default dark theme.

#### Scenario: FOUC prevention
- **WHEN** user with saved "light" theme opens the page
- **THEN** light theme is applied within the first `<script>` in `<head>` before CSS painting completes

### Requirement: Backward compatibility
The system SHALL keep dark theme as default so existing users see no change in behavior.

#### Scenario: Existing user experience
- **WHEN** a returning user has no `localStorage` entry
- **THEN** system shows the dark theme exactly as before the feature was added

# Feature Specification: Admin Timeline Management

**Feature Branch**: `001-admin-timeline-management`  
**Created**: 2026-02-13  
**Status**: Draft  
**Input**: User description: "I've created the branch 003-admin-page.  Let's plan a feature around this which creates a timeline management page.  The timeline management page is going to have the following major features. 

1. It will require authentication so we are going to need user management.  For now we are not going to worry about a password reset capability because we don't want to do email integration.  
2. We will need a role based security model.  For now, we only need two user types: admins and regular users.  We will continue to allow regular usage of the timeline application without logging in.
3. The admin page will require the admin role to load.  All of the API endpoints specific to the admin page should also require the admin permission.
4. The admin page will support a user management feature where admins can do CRUD operations on users (including password change).  
5. The admin page will have a timeline management feature which allows admins to delete timeline categories (like the Roman History timeline), edit their metadata (mostly their name), and create new categories by uploading a json file compliant with the import_schema.json"

## Clarifications

### Session 2026-02-16

- Q: What should happen if an upload references a category name that already exists? → A: Reject by default, but provide an explicit overwrite option during upload staging.
- Q: What password policy should admin-set user passwords follow? → A: Minimum 8 chars, no complexity rules.
- Q: Should uploads be processed synchronously or asynchronously? → A: Synchronous upload (request waits until ingestion completes).
- Q: Do you want a database audit log for admin actions? → A: No audit log table; use structured logs.
- Q: Should category deletion be hard delete or soft delete? → A: Hard delete categories (no soft delete).
- Q: What should the overwrite confirmation flow be? → A: UI-only confirmation; API accepts an explicit overwrite flag.
- Q: What is the max upload size? → A: 10 MB.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin access to management page (Priority: P1)

As an admin, I can sign in and access the timeline management page so that I can securely administer the system without affecting public users.

**Why this priority**: Admin access is a prerequisite for every other administrative action.

**Independent Test**: An admin can sign in and load the admin page; non-admins are denied access while public timeline access remains unchanged.

**Acceptance Scenarios**:

1. **Given** an admin account exists, **When** the admin provides valid credentials, **Then** the admin page loads successfully.
2. **Given** a non-admin account, **When** the user attempts to load the admin page, **Then** access is denied.
3. **Given** no signed-in session, **When** a visitor accesses the public timeline, **Then** the timeline remains accessible without authentication.

---

### User Story 2 - Manage users and roles (Priority: P2)

As an admin, I can create, view, update, and deactivate users and change user passwords so that access is controlled and maintained without email-based resets.

**Why this priority**: User management is required to grant and revoke administrative access.

**Independent Test**: An admin can perform CRUD on users and change passwords; non-admins cannot access user management actions.

**Acceptance Scenarios**:

1. **Given** an admin session, **When** the admin creates a user with a role, **Then** the user can sign in with that role.
2. **Given** an admin session, **When** the admin changes a user password, **Then** the user can sign in with the new password and the old password no longer works.
3. **Given** a non-admin session, **When** the user attempts any user management action, **Then** the request is denied.

---

### User Story 3 - Manage timeline categories and ingest uploads (Priority: P3)

As an admin, I can create, rename, and delete timeline categories and upload compliant JSON files to populate new categories so that timelines can be maintained.

**Why this priority**: Category maintenance and ingestion enable administrative control of timeline content.

**Independent Test**: An admin can upload a compliant file to create a category, edit its name, and delete the category with its events.

**Acceptance Scenarios**:

1. **Given** an admin session, **When** the admin uploads a compliant JSON file, **Then** a new category and its events are created.
2. **Given** an admin session, **When** the admin edits a category name, **Then** the updated name appears in the timeline list.
3. **Given** an admin session, **When** the admin deletes a category, **Then** the category and its events are removed.
4. **Given** an admin session and a category name collision, **When** the admin uploads without the overwrite flag, **Then** the upload is rejected with a clear error and the admin may re-upload with overwrite explicitly confirmed.

---

### Edge Cases

- Attempting to sign in with invalid credentials.
- Attempting admin endpoints without admin role.
- Uploading a JSON file that fails schema validation.
- Uploading a file that references a category name that already exists (default reject; allow overwrite only after explicit confirmation in the UI and an explicit overwrite flag).
- Deleting a category that contains a large number of events.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a login interface that accepts user credentials and issues an authenticated session for admins and regular users.
- **FR-002**: System MUST support two roles: admin and regular user.
- **FR-003**: System MUST restrict the admin page to users with the admin role.
- **FR-004**: System MUST restrict all admin-specific API endpoints to users with the admin role.
- **FR-005**: System MUST allow admins to create, view, update, and deactivate user accounts.
- **FR-006**: System MUST allow admins to change user passwords without email-based reset flows.
- **FR-006a**: System MUST enforce a minimum password length of 8 characters for admin-set passwords and MUST NOT require additional complexity rules.
- **FR-007**: System MUST allow unauthenticated users to continue using the public timeline without login.
- **FR-008**: System MUST allow admins to create a new timeline category by uploading a JSON file that complies with the import schema.
- **FR-009**: System MUST validate uploaded JSON files against the import schema and reject invalid uploads with a clear error.
- **FR-009a**: System MUST reject uploads that reference an existing category name by default, and MUST allow overwrite only when an explicit overwrite flag is provided by the admin UI after confirmation.
- **FR-009c**: System MUST enforce a maximum upload size of 10 MB.
- **FR-009b**: System MUST process uploads synchronously and return the final ingestion result in the same request.
- **FR-010**: System MUST allow admins to update timeline category metadata, including the category name.
- **FR-011**: System MUST allow admins to delete a timeline category and cascade-delete its associated events.
- **FR-011a**: System MUST hard delete categories (no soft delete), relying on cascade deletes for associated events and uploads.
- **FR-012**: System MUST record the category and upload metadata needed to trace the source of ingested data.

### Key Entities *(include if feature involves data)*

- **User**: Account with credentials and status, used for authentication.
- **Role**: Named access level (admin or regular user) assigned to users.
- **UserRole**: Relationship that assigns roles to users.
- **TimelineCategory**: Logical grouping of timeline events with editable metadata.
- **TimelineEvent**: Historical event associated with a timeline category.
- **IngestionUpload**: Record of an uploaded ingestion file and its outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Admin users can sign in and reach the admin page in under 2 minutes on first attempt.
- **SC-002**: 95% of valid JSON uploads result in a new category and events without manual intervention.
- **SC-003**: 100% of admin-only endpoints deny access to non-admin users.
- **SC-004**: Admins can complete user creation and password change tasks in under 3 minutes.
- **SC-005**: Deleting a category removes all associated events with no orphaned records.

## Assumptions

- No password reset via email is required for this feature.
- Public timeline browsing remains available without authentication.
- Uploaded ingestion files are processed immediately upon submission.
- Category deletion must remove associated events.

## Dependencies

- A persistent user and role store in the existing database.
- Uploads must be validated against the existing import schema.

---

description: "Task list for Admin Timeline Management implementation"
---

# Tasks: Admin Timeline Management

**Input**: Design documents from /specs/001-admin-timeline-management/
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Required (Test-First Development is non-negotiable in constitution).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: [ID] [P?] [Story] Description

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create admin schema migration in database/migrations/005_add_admin_tables.sql
- [x] T002 [P] Add Argon2 and jsonschema dependencies in api/requirements.txt

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement password hashing utility in api/auth/password_service.py
- [x] T004 [P] Add RBAC dependencies (require_roles, require_scopes) in api/auth/rbac.py
- [x] T005 Update JWT claims to include roles/scopes in api/auth/jwt_service.py and update tests in api/tests/unit/test_jwt_service.py
- [x] T006 Update auth dependency to surface principal roles in api/auth/auth_dependency.py
- [x] T007 [P] Add user data access model helpers in api/models/user.py
- [x] T008 [P] Add category/upload data access model helpers in api/models/category.py
- [x] T009 [P] Write unit tests for password hashing in api/tests/unit/test_password_service.py
- [x] T010 [P] Write unit tests for RBAC dependencies in api/tests/unit/test_rbac.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Admin access to management page (Priority: P1) 🎯 MVP

**Goal**: Admins can sign in and access the admin page; non-admins are denied while public timeline access remains unchanged.

**Independent Test**: An admin can sign in and load the admin page; non-admins cannot access admin endpoints.

### Tests for User Story 1 (Required) ⚠️

- [x] T011 [P] [US1] Add integration tests for admin login/logout/me in api/tests/integration/test_admin_auth.py

### Implementation for User Story 1

- [x] T012 [US1] Implement /admin/login, /admin/logout, /admin/me endpoints in api/api.py
- [x] T013 [US1] Add admin page shell in frontend/candidate/admin.html
- [x] T014 [US1] Implement admin login flow and session check in frontend/candidate/admin.js
- [x] T015 [US1] Add admin page styles in frontend/candidate/admin.css
- [x] T016 [US1] Add admin page navigation link in frontend/candidate/index.html

**Checkpoint**: User Story 1 should be fully functional and testable independently. Desk test the admin login/logout/me flow, then commit to the branch.

---

## Phase 4: User Story 2 - Manage users and roles (Priority: P2)

**Goal**: Admins can create, view, update, deactivate users, and change passwords; non-admins are denied.

**Independent Test**: Admin can perform CRUD and password changes; non-admin access returns 403.

### Tests for User Story 2 (Required) ⚠️

- [X] T017 [P] [US2] Write unit tests for user service in api/tests/unit/test_user_service.py
- [X] T018 [P] [US2] Write integration tests for user endpoints in api/tests/integration/test_user_endpoints.py

### Implementation for User Story 2

- [X] T019 [US2] Implement user CRUD and role assignment service in api/services/user_service.py
- [X] T020 [US2] Implement /admin/users endpoints and /admin/users/{id}/password in api/api.py
- [X] T021 [US2] Add role assignment query helpers in api/models/user.py (covered by fetch_user_roles)
- [X] T021a [US2] Add user management UI section to frontend/candidate/admin.html (table, forms, modals)
- [X] T021b [US2] Implement user CRUD operations in frontend/candidate/admin.js
  - List users with search/filtering (by email, role, active status)
  - Create user form with validation
  - Edit user modal (email, roles, activation status)
  - Delete user confirmation dialog
  - Change password form with strength validation
- [X] T021c [US2] Add user management styles in frontend/candidate/admin.css (table, forms, buttons, modals)

**Checkpoint**: User Stories 1 AND 2 should both work independently. Desk test user CRUD and password change flows, then commit to the branch.

---

## Phase 5: User Story 3 - Manage timeline categories and ingest uploads (Priority: P3)

**Goal**: Admins can create, rename, delete categories and upload JSON files to populate new categories.

**Independent Test**: Admin can upload a compliant file to create a category, edit its name, and delete the category with its events.

### Tests for User Story 3 (Required) ⚠️

- [ ] T022 [P] [US3] Write unit tests for category service validation/overwrite in api/tests/unit/test_category_service.py
- [ ] T023 [P] [US3] Write integration tests for category endpoints in api/tests/integration/test_category_endpoints.py
- [ ] T024 [P] [US3] Write integration tests for upload endpoints in api/tests/integration/test_upload_endpoints.py

### Implementation for User Story 3

- [ ] T025 [US3] Implement JSON schema validation loader in api/services/category_service.py
- [ ] T026 [US3] Implement category CRUD service in api/services/category_service.py
- [ ] T027 [US3] Implement synchronous upload processing, overwrite flag handling, 10MB size limit, and ingestion history in api/services/category_service.py
- [ ] T028 [US3] Implement /admin/categories and /admin/uploads endpoints in api/api.py
- [ ] T029 [US3] Add overwrite confirmation UI to frontend/candidate/admin.html and wiring in frontend/candidate/admin.js

**Checkpoint**: All user stories should now be independently functional. Desk test category CRUD and upload overwrite flows, then commit to the branch.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T030 [P] Add structured logging for admin actions in api/api.py
- [ ] T031 [P] Update API documentation for admin endpoints in api/README.md
- [ ] T032 Validate and update setup steps in specs/001-admin-timeline-management/quickstart.md
- [ ] T033 Run full test suite updates in api/tests/ (update as needed for any gaps)
- [ ] T034 [P] Add integration test ensuring public timeline access without auth in api/tests/integration/test_public_access.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 auth, but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Integrates with US1 auth, but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

- Task: "T011 [US1] Integration tests for admin login/logout/me in api/tests/integration/test_admin_auth.py"
- Task: "T013 [US1] Add admin page shell in frontend/candidate/admin.html"
- Task: "T014 [US1] Implement admin login flow in frontend/candidate/admin.js"

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. STOP and VALIDATE: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

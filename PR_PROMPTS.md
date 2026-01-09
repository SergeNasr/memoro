# PR Prompts for Firebase Auth Migration (Google Sign-In)

Each prompt below is ready to copy/paste into a new agent session. The agent will create a branch, implement the changes, and push to GitHub for review.

---

## PR 1: Add Firebase Dependencies and Configuration

```
I'm working on PR 1 of an incremental migration from Supabase Auth to Firebase Auth with Google Sign-In.

Reference the plan at: /Users/sergenasr/.cursor/plans/replace_supabase_auth_with_firebase_auth_(incremental)_83fd7411.plan.md

Task: PR 1 - Add Firebase Dependencies and Configuration

Goal: Add Firebase support without removing Supabase

Requirements:
1. Add `firebase-admin>=6.0.0` to `pyproject.toml` (keep `supabase>=2.22.4`)
2. Add Firebase settings to `backend/app/config.py`:
   - `firebase_project_id` (required)
   - `firebase_web_api_key` (required)
   - `firebase_service_account_path` (required)
3. Keep all existing Supabase settings unchanged

Verification: App should still work with Supabase, new config vars should be present

Workflow:
1. Create a new branch: `pr1/add-firebase-dependencies-config`
2. Make the changes
3. Run tests to ensure nothing broke
4. Commit and push to GitHub
5. Create a PR with title "PR 1: Add Firebase dependencies and configuration"
```

---

## PR 2: Create Firebase Service Module

```
I'm working on PR 2 of an incremental migration from Supabase Auth to Firebase Auth with Google Sign-In.

Reference the plan at: /Users/sergenasr/.cursor/plans/replace_supabase_auth_with_firebase_auth_(incremental)_83fd7411.plan.md

Task: PR 2 - Create Firebase Service Module

Goal: Add Firebase Auth service functions for Google Sign-In

Requirements:
1. Create `backend/app/services/firebase_auth.py` with:
   - `get_google_sign_in_url(callback_url: str)` - Generate Google Sign-In OAuth URL using Firebase Auth REST API
   - `verify_firebase_token(id_token: str)` - Verify Firebase ID token and extract user_id
2. Add unit tests for Firebase service functions
3. Use Firebase Auth REST API for OAuth URL generation
4. Use Firebase Admin SDK for token verification

Verification: New service can be imported, functions work independently

Workflow:
1. Create a new branch: `pr2/create-firebase-service`
2. Make the changes
3. Run tests to ensure everything works
4. Commit and push to GitHub
5. Create a PR with title "PR 2: Create Firebase service module"
```

---

## PR 3: Add Firebase Auth Functions (Parallel to Supabase)

```
I'm working on PR 3 of an incremental migration from Supabase Auth to Firebase Auth with Google Sign-In.

Reference the plan at: /Users/sergenasr/.cursor/plans/replace_supabase_auth_with_firebase_auth_(incremental)_83fd7411.plan.md

Task: PR 3 - Add Firebase Auth Functions (Parallel to Supabase)

Goal: Add Firebase auth functions alongside existing Supabase functions

Requirements:
1. Update `backend/app/auth.py`:
   - Add `get_firebase_client()` function (initializes Firebase Admin SDK)
   - Add `get_current_user_firebase(request: Request) -> UUID` function (parallel to `get_current_user()`)
   - Keep all existing Supabase functions unchanged
2. Use Firebase Admin SDK `verify_id_token()` for token validation
3. Extract user_id from Firebase token claims (`user_id` field)

Verification: Both auth systems can coexist, existing Supabase auth still works

Workflow:
1. Create a new branch: `pr3/add-firebase-auth-functions`
2. Make the changes
3. Run tests to ensure nothing broke
4. Commit and push to GitHub
5. Create a PR with title "PR 3: Add Firebase auth functions (parallel to Supabase)"
```

---

## PR 4: Add Firebase Auth Routes (Parallel Routes)

```
I'm working on PR 4 of an incremental migration from Supabase Auth to Firebase Auth with Google Sign-In.

Reference the plan at: /Users/sergenasr/.cursor/plans/replace_supabase_auth_with_firebase_auth_(incremental)_83fd7411.plan.md

Task: PR 4 - Add Firebase Auth Routes (Parallel Routes)

Goal: Add Firebase auth endpoints alongside Supabase endpoints

Requirements:
1. Update `backend/app/routers/auth.py`:
   - Add `/auth/firebase/login` (GET) - Redirect to Google Sign-In OAuth URL using `get_google_sign_in_url()` from firebase_auth service
   - Add `/auth/firebase/callback` - Handle Firebase callback with `id_token` query param, verify token using `verify_firebase_token()`, set cookie
   - Keep all existing Supabase routes unchanged (`/auth/login`, `/auth/callback`)
2. Add tests for Firebase routes
3. Use the same cookie configuration as Supabase routes (COOKIE_NAME, max_age, etc.)

Verification: Both `/auth/login` (Supabase) and `/auth/firebase/login` (Firebase) work independently

Workflow:
1. Create a new branch: `pr4/add-firebase-routes`
2. Make the changes
3. Run tests to ensure both systems work
4. Commit and push to GitHub
5. Create a PR with title "PR 4: Add Firebase auth routes (parallel routes)"
```

---

## PR 5: Update Login Template for Google Sign-In

```
I'm working on PR 5 of an incremental migration from Supabase Auth to Firebase Auth with Google Sign-In.

Reference the plan at: /Users/sergenasr/.cursor/plans/replace_supabase_auth_with_firebase_auth_(incremental)_83fd7411.plan.md

Task: PR 5 - Update Login Template for Google Sign-In

Goal: Add Google Sign-In button to login page

Requirements:
1. Update `backend/app/templates/login.html`:
   - Add Google Sign-In button that links to `/auth/firebase/login`
   - Keep existing email form for Supabase (or show both options)
   - Style the Google Sign-In button appropriately
2. Keep Supabase login flow working

Verification: Login page shows both Google Sign-In and email form options

Workflow:
1. Create a new branch: `pr5/update-login-template`
2. Make the changes
3. Test both login flows
4. Commit and push to GitHub
5. Create a PR with title "PR 5: Update login template for Google Sign-In"
```

---

## PR 6: Switch Main Code to Use Firebase + Add Comprehensive Tests

```
I'm working on PR 6 of an incremental migration from Supabase Auth to Firebase Auth with Google Sign-In.

Reference the plan at: /Users/sergenasr/.cursor/plans/replace_supabase_auth_with_firebase_auth_(incremental)_83fd7411.plan.md

Task: PR 6 - Switch Main Code to Use Firebase + Add Comprehensive Tests

Goal: Replace Supabase calls with Firebase in main routes and auth functions, and add comprehensive tests

Requirements:
1. Update `backend/app/routers/auth.py`:
   - Replace `/auth/login` (GET) to redirect to Firebase Google Sign-In instead of showing email form
   - Replace `/auth/callback` to use Firebase token verification (`verify_firebase_token()`) instead of Supabase
   - Keep Supabase code commented or in separate functions for rollback
2. Update `backend/app/auth.py`:
   - Replace `get_current_user()` to call `get_current_user_firebase()` instead of Supabase validation
   - Keep Supabase functions present (commented or unused) for rollback
3. Update `backend/app/templates/login.html`:
   - Update to show Google Sign-In as primary option
4. Add comprehensive Firebase tests:
   - Update `backend/tests/test_auth.py`: Add tests for `get_current_user_firebase()` and updated `get_current_user()`, mock Firebase Admin SDK
   - Update `backend/tests/test_auth_routes.py`: Update tests for Firebase routes (`/auth/login`, `/auth/callback`), mock Firebase Auth REST API calls and token verification
   - Update `backend/tests/conftest.py`: Add Firebase mocks

Verification: Main auth flow uses Firebase Google Sign-In, all tests pass, Supabase code still present for rollback if needed

Workflow:
1. Create a new branch: `pr6/switch-to-firebase-with-tests`
2. Make the changes
3. Run all tests to ensure everything passes
4. Commit and push to GitHub
5. Create a PR with title "PR 6: Switch main code to use Firebase + add comprehensive tests"
```

---

## PR 7: Remove Supabase Code (Final Cleanup)

```
I'm working on PR 7 of an incremental migration from Supabase Auth to Firebase Auth with Google Sign-In.

Reference the plan at: /Users/sergenasr/.cursor/plans/replace_supabase_auth_with_firebase_auth_(incremental)_83fd7411.plan.md

Task: PR 7 - Remove Supabase Code (Final Cleanup)

Goal: Remove Supabase after Firebase is verified working

Requirements:
1. Remove `supabase>=2.22.4` from `pyproject.toml`
2. Remove Supabase settings from `backend/app/config.py`:
   - `supabase_url`
   - `supabase_secret_key`
3. Remove Supabase functions from `backend/app/auth.py`:
   - `get_supabase_client()`
   - Any commented/unused Supabase code
4. Remove Supabase routes from `backend/app/routers/auth.py`:
   - Any commented/unused Supabase route code
5. Remove Supabase mocks from `backend/tests/conftest.py`
6. Rename `get_current_user_firebase()` to `get_current_user()` (if not already done in PR 6)
7. Rename `COOKIE_NAME` from `"supabase_access_token"` to `"access_token"`
8. Remove `/auth/firebase/*` route prefixes (routes should already use default paths from PR 6)
9. Clean up login template to only show Google Sign-In

Verification: Only Firebase auth remains, all tests pass

Workflow:
1. Create a new branch: `pr7/remove-supabase-cleanup`
2. Make the changes
3. Run all tests to ensure everything passes
4. Commit and push to GitHub
5. Create a PR with title "PR 7: Remove Supabase code (final cleanup)"
```

---

## Usage Instructions

1. Copy the prompt for the PR you want to work on
2. Paste it into a new agent session
3. The agent will create a branch, implement changes, and push to GitHub
4. Review the PR and merge when ready
5. Move to the next PR

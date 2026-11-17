# Contract notes
`openapi.json` is generated from the backend (`app.openapi()`). The frontend's `mock/server.js` is the original contract; the real
API matches it except for these deliberate differences:
1. List endpoints (`/applications/mine`, `/admin/applications`, `/reviewer/applications`) return slim items
   (id, student_id, student_name, scholarship_id, scholarship_title, status, created_at, updated_at); full data is in `GET /applications/{id}`.
2. `POST /applications` returns 200 (not 201) when it resumes an existing application.
3. A reviewer reviewing an application that is not yet VERIFIED gets 404 (they cannot see it), not 409.
4. Register reports field errors in order of validation; a duplicate email is reported once the other fields are valid.
5. Stricter rules: admin reject and reviewer "request changes" require remarks; uploads limited to PDF/JPG/PNG up to 5 MB.

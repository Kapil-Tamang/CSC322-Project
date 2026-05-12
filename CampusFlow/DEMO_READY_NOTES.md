# CampusFlow Demo-Ready Notes

This version includes the UI/behavior fixes requested after manual testing.

## Run

Terminal 1:
```bash
cd CSC322-Project-main/CampusFlow1/backend
python3 -m pip install -r requirements.txt
python3 main.py
```

Terminal 2:
```bash
cd CSC322-Project-main/CampusFlow1/frontend
npm install
npm run dev
```

Open the URL shown by Vite, usually http://127.0.0.1:5173.

## Demo accounts

- Registrar: `registrar` / `registrar123`
- Instructor: `prof_chen` / `pass123`
- Student: `S1001` / `pass123`

Approved applicants use their requested username and temporary password `changeme123`. On first login they must change the password.

## Important demo flow notes

- To create a course, sign in as registrar, go to Registrar Admin, set phase to `class set-up period`, click Update Phase, then create the course.
- To let students register, set phase to `course registration period`.
- To submit grades, set phase to `grading period`, then sign in as instructor.
- Course Cancellation Checks are for `class running period`.
- Final Grade/GPA Checks are for grading review. They create GPA questions only once per course/instructor, so repeated clicks do not spam duplicates.

## Fixes included

- Visitor page layout no longer overflows and the College0 typo was removed.
- Creative feature banner and System/React+FastAPI card were removed.
- Refresh buttons now show feedback and reload data.
- Registrar phase changes, course creation, and phase-dependent flows work.
- Applications show the temporary password for approved users.
- Approved users can sign in with `changeme123` and are forced to change it.
- Instructor grading uses a dropdown instead of a broken NaN enrollment input.
- Waitlist section explains when there are no waitlisted students.
- GPA justifications are manually written by the instructor.
- Duplicate GPA questions are prevented.
- Student registration, graduation apply, and review submission show clear messages.
- Students can see visible class reviews; registrar can see reviewer identities.
- Tables were cleaned up for demo readability.

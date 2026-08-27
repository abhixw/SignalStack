class UserRole:
    ADMIN = "admin"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"

    ALL = (ADMIN, RECRUITER, CANDIDATE)
    SELF_REGISTERABLE = (RECRUITER, CANDIDATE)  # admin accounts are provisioned separately


class JobRole:
    """A fixed, small list rather than free text — free text on the recruiter
    side ("Backend Dev" vs "backend developer" vs "Backend Engineer") would
    fragment candidate-side filtering into near-duplicates that never match."""
    BACKEND = "Backend Engineer"
    FRONTEND = "Frontend Engineer"
    FULL_STACK = "Full Stack Engineer"
    MOBILE = "Mobile Engineer"
    DATA_ML = "Data Scientist / ML Engineer"
    DEVOPS = "DevOps / Infrastructure Engineer"
    QA = "QA / Test Engineer"
    GENERAL_SDE = "Software Engineer (General)"

    ALL = (BACKEND, FRONTEND, FULL_STACK, MOBILE, DATA_ML, DEVOPS, QA, GENERAL_SDE)

from .task import Task, TaskSuggestionRequest, TaskSuggestion
from .outcome import OutcomeCreate
from .proof import ProofCreate, Evidence
from .evaluation import EvaluateRequest, EvaluationTrigger, WorkAllocation, TaskScore, EvaluationResponse, EvaluationSummary, CandidateDecisionUpdate, FeedbackSuggestionRequest
from .feedback import FeedbackCreate, SignalWeightResponse
from .candidate import CodingProfilesUpdate
from .auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    Token,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
    GithubOtpVerifyRequest,
    GithubOtpVerifyResponse,
    GithubEmailConfirmRequest,
    CandidateRegisterStart,
)

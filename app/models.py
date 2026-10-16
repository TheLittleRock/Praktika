from typing import List, Optional, Any, Union, Dict
from pydantic import BaseModel, Field

# Auth & Users
class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "assistant" # 'admin' or 'assistant'

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: Optional[bool] = True

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class AdminPasswordResetRequest(BaseModel):
    new_password: str

class ProfileUpdateRequest(BaseModel):
    full_name: str

class UserAdminUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

# Semesters
class SemesterCreate(BaseModel):
    code: str
    name: str
    is_active: bool = True

class SemesterUpdate(BaseModel):
    code: str
    name: str

class SemesterResponse(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool

# Slots / Termíny
class SlotCreate(BaseModel):
    semester_id: int
    name: str
    day_of_week: str
    time_start: str
    time_end: str
    room: Optional[str] = ""
    course_code: str = "FPRA1" # 'FPRA1', 'FPRA2', 'ZFM2'

class SlotUpdate(BaseModel):
    name: Optional[str] = None
    day_of_week: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    room: Optional[str] = None
    course_code: Optional[str] = None

class SlotResponse(BaseModel):
    id: int
    semester_id: int
    name: str
    day_of_week: str
    time_start: str
    time_end: str
    room: Optional[str]
    course_code: Optional[str] = "FPRA1"

class MeasurementCreate(BaseModel):
    code: str
    number: int
    name: str
    course_code: str = "FPRA1" # 'FPRA1', 'FPRA2', 'ZFM2'
    semester_type: Optional[str] = "ZS" # 'ZS', 'LS', 'ZFM'
    description: Optional[str] = ""
    instructions_text: Optional[str] = ""

class MeasurementUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    number: Optional[int] = None
    course_code: Optional[str] = None
    semester_type: Optional[str] = None
    description: Optional[str] = None
    instructions_text: Optional[str] = None

class MeasurementResponse(BaseModel):
    id: int
    code: str
    number: int
    name: str
    course_code: Optional[str] = "FPRA1"
    semester_type: Optional[str] = "ZS"
    description: Optional[str] = None
    instructions_text: Optional[str] = ""

# Presets (časté chyby / rychlé komentáře)
class PresetCreate(BaseModel):
    type: str # 'deduction' or 'comment'
    category: str = "obecne" # 'vysledky', 'diskuze', 'format', 'chyby', 'obecne'
    pts: float = 0.0
    text: str
    user_id: Optional[int] = None

class PresetResponse(BaseModel):
    id: int
    type: str
    category: str
    pts: float
    text: str
    user_id: Optional[int] = None

# Deductions and Evaluation
class DeductionItem(BaseModel):
    category: str # vysledky, diskuze, format, chyby
    pts: float
    reason: str

class EvaluationSaveRequest(BaseModel):
    protocol_id: Optional[int] = None
    vysledky_score: float
    diskuze_score: float
    format_score: float
    chyby_score: float
    total_points: float
    grade: str
    manual_grade_override: Optional[Union[str, bool]] = None
    deductions: List[DeductionItem] = []
    annotations: Optional[List[Any]] = None
    raw_output_1: str = ""
    raw_output_2: str = ""
    burn_to_pdf: bool = True
    status: Optional[str] = "graded" # 'graded', 'revision', 'in_progress'

class AutosaveRequest(BaseModel):
    protocol_id: Optional[int] = None
    annotations: Optional[List[Any]] = None
    evaluation: Optional[EvaluationSaveRequest] = None
    ai_proposals: Optional[Dict[str, Any]] = None
    vysledky_score: Optional[float] = None
    diskuze_score: Optional[float] = None
    format_score: Optional[float] = None
    chyby_score: Optional[float] = None
    total_points: Optional[float] = None
    grade: Optional[str] = None
    deductions: Optional[List[DeductionItem]] = None
    raw_output_1: Optional[str] = None
    raw_output_2: Optional[str] = None

class ProtocolAssignRequest(BaseModel):
    evaluator_id: Optional[int] = None

class ProtocolMetadataUpdateRequest(BaseModel):
    student_name: str
    semester_id: int
    slot_id: int
    measurement_id: int

class BulkDeleteRequest(BaseModel):
    protocol_ids: List[int]

class BulkUpdateRequest(BaseModel):
    protocol_ids: List[int]
    semester_id: Optional[int] = None
    slot_id: Optional[int] = None
    measurement_id: Optional[int] = None
    evaluator_id: Optional[int] = None

class AnnotationSaveRequest(BaseModel):
    protocol_id: int
    annotations: List[Any] = [] # list of drawings, notes, text_direct, highlights, shapes

class AISettingsRequest(BaseModel):
    api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    personal_gemini_api_key: Optional[str] = None
    model_name: Optional[str] = "gemini-3.5-flash"
    ai_enabled: Optional[bool] = True
    auto_analyze_on_upload: Optional[bool] = True
    ai_language: Optional[str] = "cs"
    guidelines: Optional[str] = None

class AIDeductionSuggestion(BaseModel):
    proposal_id: Optional[str] = None
    category: str # vysledky, diskuze, format, chyby
    pts: float
    points: Optional[float] = None
    reason: str
    page: Optional[int] = None

    def __init__(self, **data):
        if "points" in data and "pts" not in data:
            data["pts"] = data["points"]
        elif "pts" in data and "points" not in data:
            data["points"] = data["pts"]
        super().__init__(**data)

class AIAnnotationSuggestion(BaseModel):
    proposal_id: Optional[str] = None
    page: int
    type: str = "highlight" # highlight, strikeout, note
    search_text: Optional[str] = None
    comment: str
    rect: Optional[List[float]] = None
    point: Optional[List[float]] = None

class AIAnalysisResult(BaseModel):
    protocol_id: int
    scores: dict
    deductions: List[AIDeductionSuggestion]
    annotations: List[AIAnnotationSuggestion]
    summary: str
    model_used: Optional[str] = "Gemini Flash"
    preferred_model: Optional[str] = None
    fallback_note: Optional[str] = None

class AutodetectResponse(BaseModel):
    student_name: Optional[str] = ""
    course_code: Optional[str] = "FPRA1"
    measurement_id: Optional[int] = None
    measurement_name: Optional[str] = ""
    measurement_number: Optional[int] = None
    task_number: Optional[int] = None
    slot_id: Optional[int] = None
    slot_name: Optional[str] = ""
    semester_id: Optional[int] = None
    day_of_week: Optional[str] = ""
    time_start: Optional[str] = ""
    raw_text_sample: Optional[str] = ""
    raw_text_preview: Optional[str] = ""
    detected_fields: List[str] = []
class AIProposalActionRequest(BaseModel):
    action: str  # approve_annotation, reject_annotation, approve_deduction, reject_deduction, approve_all_annotations, approve_all_deductions
    proposal_id: Optional[str] = None
    annotation_data: Optional[Dict[str, Any]] = None

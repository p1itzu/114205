from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import re
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    驗證密碼強度
    返回: (是否通過, 錯誤訊息)
    
    密碼要求:
    - 至少8個字符
    - 包含至少一個大寫字母
    - 包含至少一個小寫字母  
    - 包含至少一個數字
    """
    if len(password) < 8:
        return False, "密碼長度至少需要8個字符"
    
    if not re.search(r'[A-Z]', password):
        return False, "密碼必須包含至少一個大寫字母"
    
    if not re.search(r'[a-z]', password):
        return False, "密碼必須包含至少一個小寫字母"
    
    if not re.search(r'\d', password):
        return False, "密碼必須包含至少一個數字"
    
    return True, ""

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

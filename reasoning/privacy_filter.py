import re
import os

class PrivacyFilter:
    """
    v2 요구사항: LLM 전송 전 프로세스명, 파일 경로, 사용자 프로필 등의 개인정보 마스킹
    """
    @staticmethod
    def sanitize(data: dict) -> dict:
        import copy
        sanitized = copy.deepcopy(data)
        
        # 1. 사용자 프로필 경로 마스킹 (예: C:\Users\Username\... -> C:\Users\<user>\...)
        user_profile = os.environ.get('USERPROFILE', '')
        if user_profile:
            username = os.path.basename(user_profile)
            if username:
                # 데이터 내 모든 문자열에서 사용자명 치환
                sanitized = PrivacyFilter._recursive_mask(sanitized, username, "<user>")

        return sanitized

    @staticmethod
    def _recursive_mask(obj, target: str, replacement: str):
        if isinstance(obj, str):
            # 대소문자 무시하고 사용자 이름 마스킹
            pattern = re.compile(re.escape(target), re.IGNORECASE)
            return pattern.sub(replacement, obj)
        elif isinstance(obj, dict):
            return {k: PrivacyFilter._recursive_mask(v, target, replacement) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [PrivacyFilter._recursive_mask(item, target, replacement) for item in obj]
        return obj

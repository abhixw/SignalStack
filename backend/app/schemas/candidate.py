from typing import Optional

from pydantic import BaseModel


class CodingProfilesUpdate(BaseModel):
    # None = leave unchanged; "" = clear it; non-empty = fetch, validate, store.
    codeforces_handle: Optional[str] = None
    leetcode_username: Optional[str] = None

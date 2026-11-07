"""Server-side validation; explicit real0 is valid, missing experience is not0."""
import math,re,unicodedata

class ValidationError(ValueError):pass


def validate_batch(payload,catalog):
 if not isinstance(payload,dict)or set(payload)-{'ratings','request_id'}:raise ValidationError('지원하지 않는 제출 필드입니다.')
 rows=payload.get('ratings');key=payload.get('request_id')
 if not isinstance(key,str)or not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}',key):raise ValidationError('유효한 제출 식별자가 필요합니다.')
 if not isinstance(rows,list)or not 1<=len(rows)<=479:raise ValidationError('경험한 향수 1개 이상을 입력해 주세요. 3개만 평가해도 됩니다.')
 seen=set();clean=[]
 for r in rows:
  if not isinstance(r,dict)or set(r)-{'perfume_id','rating','experience_type','confidence','preference_reason'}:raise ValidationError('지원하지 않는 평점 필드입니다.')
  i=r.get('perfume_id');y=r.get('rating')
  if not isinstance(i,str)or i not in catalog:raise ValidationError('서비스 후보에 없는 향수입니다.')
  if i in seen:raise ValidationError('같은 제출에 동일한 향수가 중복되어 있습니다.')
  seen.add(i)
  if r.get('experience_type')not in('used','sampled'):raise ValidationError('실제 사용 또는 시향한 향수만 평가할 수 있습니다.')
  if isinstance(y,bool)or not isinstance(y,(int,float))or not math.isfinite(y)or not 0<=y<=10 or abs(y*2-round(y*2))>1e-9:raise ValidationError('평점은 0~10점, 0.5점 단위여야 합니다.')
  confidence=r.get('confidence','')
  if confidence not in('','low','medium','high'):raise ValidationError('경험 신뢰도 값이 올바르지 않습니다.')
  reason=r.get('preference_reason','')
  if not isinstance(reason,str)or len(reason)>300:raise ValidationError('선호 이유는 300자 이하로 입력해 주세요.')
  reason=unicodedata.normalize('NFC',reason).strip()
  if any(unicodedata.category(c).startswith('C')for c in reason):raise ValidationError('제어문자·줄바꿈은 입력할 수 없습니다.')
  if re.search(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|(?:\+?82[ -]?)?0?1[016789][ -]?\d{3,4}[ -]?\d{4}',reason):raise ValidationError('선호 이유에 이메일·전화번호를 입력하지 마세요.')
  clean.append(dict(perfume_id=i,rating=float(round(y*2)/2),experience_type=r['experience_type'],confidence=confidence,preference_reason=reason))
 return clean,key


def csv_safe(value):
 """Neutralize spreadsheet formulas in text fields; numerical ratings stay numeric."""
 if isinstance(value,str)and value.lstrip(' \ufeff').startswith(('=','+','-','@','\t','\r','\n')):return "'"+value
 return value

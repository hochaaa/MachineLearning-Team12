"""Presentation-only input validation/output formatting around unchanged demo_frozen.py.

No model fitting, new scoring formula or candidate policy is implemented here.
This wrapper accepts exact catalog URLs, not perfume-name/user-ID lookup.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from perfume.data import fragrantica


def read(path):
    """Read local JSON path; never loads validation/test/externally held-out answers."""
    with Path(path).open(encoding='utf-8') as stream:return json.load(stream)


def prepare(root,support_path,required,forbidden,preferred):
    """Check existing freeze hashes and public-catalog input. No weights are fitted/scored.

    root: original project or isolated test mirror; support_path: independent example JSON.
    required/forbidden/preferred: exact existing note:/accord: tokens, not a new taxonomy.
    """
    manifest=root/'outputs/final/freeze.json'
    if not manifest.is_file():raise ValueError('동결 manifest 파일이 없습니다. 준비된 프로젝트 사본을 확인하세요.')
    freeze=read(manifest)
    for name,expected in freeze['protected_sha256'].items():
        path=root/name
        if not path.is_file():raise ValueError(f'필수 보호 파일이 없습니다: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'동결 파일 무결성 검사가 실패했습니다: {name}. 모델을 다시 만들지 말고 검증된 사본을 복원하세요.')
    if not support_path.is_file():raise ValueError('취향 입력 JSON 파일을 찾을 수 없습니다.')
    support=read(support_path)
    if not isinstance(support,list):raise ValueError('입력은 [[향수 URL, 0~1 평점], ...] 형식의 JSON 배열이어야 합니다.')
    catalog,_=fragrantica(root/'Term-project-datasets/fra_cleaned.csv')
    seen=set()
    for row in support:
        if not isinstance(row,list) or len(row)!=2:raise ValueError('각 입력 행은 [향수 URL, 평점] 두 항목이어야 합니다.')
        item,rating=row
        if not isinstance(item,str) or item not in catalog:
            raise ValueError('알 수 없는 향수입니다. 제품명 검색은 지원하지 않으며 카탈로그의 정확한 URL을 입력해야 합니다.')
        if isinstance(rating,bool) or not isinstance(rating,(int,float)) or not math.isfinite(rating) or not 0<=rating<=1:
            raise ValueError('평점은 0부터 1 사이의 유한 숫자여야 합니다. 문자열·true/false는 허용하지 않습니다.')
        if item in seen:raise ValueError('동일 향수를 중복 입력했습니다. 향수마다 한 번만 입력하세요.')
        seen.add(item)
    candidates=read(root/freeze['candidates_path'])
    tokens={t for i in candidates for t in catalog[i]['tokens']}
    for token in required+forbidden+preferred:
        if token not in tokens:raise ValueError('현재 후보 카탈로그에 없는 조건입니다. accord:woody, accord:floral, note:rose 등 검증된 token을 입력하세요.')
    factors=set(read(root/'outputs/final/model.json')['items'])
    return support,sum(i in factors for i,_ in support)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support',required=True,help='별도 합성/동의받은 입력 JSON; 원본 사용자 이력이나 test 정답 사용 금지')
    parser.add_argument('--k',type=int,default=5)
    parser.add_argument('--required',action='append',default=[])
    parser.add_argument('--forbidden',action='append',default=[])
    parser.add_argument('--preferred',action='append',default=[])
    parser.add_argument('--json',action='store_true',help='기존 CLI의 JSON 결과 그대로 출력')
    parser.add_argument('--project-root',type=Path,default=PROJECT,help='기본값은 이 스크립트의 프로젝트. 격리된 기능 테스트 사본에도 사용')
    args=parser.parse_args()
    try:
        if args.k<1:raise ValueError('추천 개수 K는 1 이상의 정수여야 합니다.')
        root=args.project_root.resolve();support_path=Path(args.support).expanduser().resolve()
        support,factor_count=prepare(root,support_path,args.required,args.forbidden,args.preferred)
        command=[sys.executable,'-B',str(PROJECT/'scripts/demo_frozen.py'),'--support',str(support_path),'--k',str(args.k)]
        for flag,values in [('--required',args.required),('--forbidden',args.forbidden),('--preferred',args.preferred)]:
            for value in values:command.extend([flag,value])
        result=subprocess.run(command,cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=60)
        if result.returncode:
            raise ValueError('저장 모델의 기존 추론 CLI 실행에 실패했습니다. 기능 검증 기록과 보호 파일을 확인하세요. 재학습하지 마세요.')
        payload=json.loads(result.stdout)
        if args.json:print(result.stdout,end='');return 0
        print('Team 12 향수 추천 시연 | 독립 입력 예시, 평가 성능 측정 아님')
        print(f'입력 {len(support)}개 · 요청 Top-{args.k} · 동결 Hybrid alpha={payload["alpha"]}')
        if not support:print('평점 이력이 없어 학습 인기도 폴백으로 추천합니다. 개인화 추천이 아닙니다.')
        elif not factor_count:print('입력 상품에 학습된 MF factor가 없어 콘텐츠/인기도 폴백을 사용합니다.')
        else:print(f'MF factor가 있는 입력 {factor_count}개로 신규 사용자 fold-in; 기존 item factors는 고정됩니다.')
        if args.required:print('필수 조건: '+', '.join(args.required))
        rows=payload['results']
        if not rows:print('조건을 만족하는 추천 가능한 향수가 없습니다. 조건을 완화하거나 다른 취향을 입력하세요.');return 0
        if len(rows)<args.k:print(f'현재 조건에서 {len(rows)}개만 추천할 수 있습니다.')
        for n,row in enumerate(rows,1):
            explanation=row['explanation'];shared=', '.join(explanation['shared_tokens'][:6]) or '공통 토큰 없음'
            print(f'{n}. {row["name"]} / {row["brand"]} | 추천 점수 {row["score"]:.4f}')
            print(f'   메타데이터 근거: {shared}; 필수조건 충족={explanation["required_satisfied"]}')
        print('점수는 선호 확률이 아닙니다. 공통 토큰은 향 특성 겹침이며 MF의 인과적 설명이 아닙니다.')
        return 0
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError,subprocess.TimeoutExpired) as error:
        print('오류: '+str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())

# 이터널 다크니스 (GC) 한글 패치

*Eternal Darkness: 招かれた13人* (게임큐브, 일본판 `GEDJ01`) 비공식 한국어 팬 패치입니다.
대사는 북미판 영어 원문을 기준으로 번역하고, 높임과 칸 나눔은 일본판을 참고했습니다.

**제작: arqhive** · **최신 버전: [v0.2.1](../../releases/tag/v0.2.1)**

- 컷신·실시간 자막, 방 조사 문구, 책(소지품·스펠·저널·부검) 화면, 메뉴·메모리 카드 문구를 한글화했습니다(3,376줄).
- 그림 글씨 113장을 한글화했습니다(부검 그림 메모, 책 화면 버튼·탭, 타이틀·옵션 메뉴, 엔딩 화면, 포 인용 화면).
- 타이틀 로고와 프롤로그 책 표지 로고는 북미판 로고(Sanity's Requiem)로 바꿨습니다.
- 게임 설정의 언어 「日本語」 자리가 「한국어」가 됩니다.
- **원본과 같은 1.4GB 디스크 크기를 유지합니다.**

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 일본판(`GEDJ01`) 이미지. ISO·GCM은 그대로, CISO·WIA·WDF·GCZ는 패처가 ISO로 바꿔서 적용합니다.
- Windows 10 이상(기본 PowerShell 사용). 다른 도구는 필요 없습니다.

| 원본 형식 | 결과 | 비고 |
|---|---|---|
| ISO, GCM | ISO | |
| CISO, WIA, WDF, GCZ | ISO | 동봉한 wit으로 ISO로 바꾼 뒤 적용 |
| RVZ | 지원 안 함 | Dolphin에서 ISO로 변환한 뒤 적용 |
| NKit | 지원 안 함 | NKit 도구로 원래 ISO로 되돌린 뒤 적용 |

패처가 게임 파일 하나하나를 원본과 비교하므로, 덤프 방식에 따라 ISO 전체 MD5가 달라도 게임 파일만 같으면 적용됩니다. 북미판·유럽판과 이미 한글 패치를 적용한 이미지에는 적용되지 않습니다.

### 적용 방법

1. [배포 페이지](../../releases/tag/v0.2.1)에서 `GEDJ_KPatch_v0.2.1.zip`을 받아 풉니다.
2. 풀린 폴더에 원본 이미지를 넣고 `패치하기.bat`을 더블클릭합니다. 원본 파일을 `패치하기.bat` 위에 끌어다 놓아도 됩니다.
3. 원본과 같은 폴더에 `Eternal Darkness (Korean).iso`가 생깁니다. 원본 파일은 그대로 남습니다.

결과 파일 이름을 바꾸려면 두 번째 인자로 지정합니다. 오류 메시지와 자세한 방법은 ZIP에 들어 있는 `README.txt`를 참고하세요.

```bash
패치하기.bat "Eternal Darkness - Manekareta 13-nin (Japan).iso" "D:/Games/Eternal Darkness (Korean).iso"
```

### 원본 확인값

Redump 정본 ISO의 값입니다. 다른 덤프도 게임 파일이 같으면 적용됩니다. 정본에 적용하면 패처가 마지막에 「정본(Redump) 원본 기준 결과와 일치합니다」를 출력합니다.

| 항목 | 원본 일본판 |
|---|---|
| 크기 | 1,459,978,240 바이트 |
| CRC32 | `AF4D0E9E` |
| MD5 | `ae427c8f680f7c9dbb2a9b17c7583de6` |
| SHA-1 | `c176d3afcf151f743d7f45d56330916ea1756b1a` |

원본 파일명 예: `Eternal Darkness - Manekareta 13-nin (Japan).iso`

### 실행 환경

- **확인함**: Dolphin.

### 알려진 문제

- 오프닝 영상의 타이틀 부제(일본어)는 영상 안에 그려져 있어 그대로 두었습니다.
- 숫자만 있는 그림(16:9, 4:3)과 일본판에서도 영어였던 디자인 글자(Press A to Continue 등)는 그대로 두었습니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3.11 이상과 numpy, Pillow, opencv-python, unicorn(압축 해제 에뮬레이션).
- 일본판 ISO(`Eternal Darkness - Manekareta 13-nin (Japan).iso`)를 저장소 루트에. 그림 영어판 대조용으로 북미판 ISO도 씁니다.
- 한글 자막 글꼴 본고딕(Noto Sans KR) 가변 글꼴(`work/fonts/NotoSansKR-VF.ttf`, 굵기 400). 그림 글씨를 다시 만들 때는 연천 허목체 등 아래 「글꼴」의 글꼴과 LaMa 인페인팅(PyTorch, big-lama)이 필요합니다.
- 배포용 패처를 만들 때만: xdelta3 3.1.0과 wit v3.05a(cygwin64판). 릴리즈 ZIP의 `bin/`에 든 것을 그대로 써도 됩니다.

### 빌드

```bash
python tools/dump.py "Eternal Darkness - Manekareta 13-nin (Japan).iso" extract/jp
python tools/dump.py "Eternal Darkness - Sanity's Requiem (USA).iso" extract/us
python tools/dec_all.py         # SK_ASC 압축 해제 → extract/dec/{jp,us}
python tools/extract_text.py    # 번역 단위 표(원문) → work/text/units.json
python tools/build_full.py      # 번역·폰트·폭 표·그림·DOL → build/full
python tools/build_iso.py "Eternal Darkness - Manekareta 13-nin (Japan).iso" build/ED_KR.iso \
    --dol build/full/main.dol --repdir build/full --pack
python tools/make_patcher.py --orig "Eternal Darkness - Manekareta 13-nin (Japan).iso" --build build/ED_KR.iso \
    --out release/GEDJ_KPatch_v0.2.1 --version 0.2.1 --wit <wit 폴더> --xdelta <xdelta3.exe> --readme patcher/README.txt
```

- 이 게임의 데이터 파일은 산술부호 압축(SK_ASC)이라 다시 압축하는 도구가 없습니다. 그래서 DOL의 압축 해제 함수에 「표식이 없으면 그대로 복사」하는 우회를 넣고(`tools/patch_dol.py`), 바뀐 파일은 푼 상태로 넣습니다.
- 푼 파일이 커져 디스크 뒤쪽 빈 영역(55MB)만으로는 모자라므로, `build_iso.py --pack`이 바뀌는 파일 자리를 모두 비운 뒤 큰 파일부터 빈자리에 다시 놓습니다. 패처는 그 위치를 그대로 쓰므로 정본에 적용한 결과가 빌드 ISO와 MD5까지 같습니다.
- 한글은 일본어 가나·한자 칸(0x120~)에 그려 넣습니다. 쓰인 글자 1,011자라 원래 폰트 칸 안에 들어가고, 폰트 장 추가나 폭 표 확장은 하지 않았습니다.
- 그림 확정본(`work/gfx/done/`)은 게임 그림에서 만든 것이라 저장소에 넣지 않았습니다. `tools/gfx_*.py`와 `work/gfx/`의 설정으로 다시 만들 수 있습니다.

### 번역 수정

- 번역문: `work/text/ko/*.json`(항목 이름과 한국어). 고친 뒤 `python tools/check_trans.py work/text/ko/<파일>.json`으로 태그·창 넘침·문장부호·높임을 검사하고 빌드합니다.
- 용어·표기: [`docs/glossary.md`](docs/glossary.md), 번역 규칙: [`docs/translation_rules.md`](docs/translation_rules.md), 창 크기: [`docs/windows.md`](docs/windows.md), 그림 규칙: [`docs/graphics_rules.md`](docs/graphics_rules.md).
- 일본어·영어 원문은 게임 데이터라 넣지 않았습니다. 원문이 필요한 도구를 쓰려면 직접 가진 ISO에서 `tools/extract_text.py`로 다시 뽑으세요.

### 폴더 구조

```
tools/          추출·압축 해제·번역 검사·그림 제작·빌드·패처 도구
work/text/ko/   번역 JSON (항목 이름과 한국어)
work/gfx/       그림 목록(plan.tsv)과 그림별 설정
docs/           분석·추출·용어집·번역 규칙·창 크기·그림 규칙·검수 보고서
patcher/        사용자용 패처(patch.ps1, 패치하기.bat)와 설명서 README.txt
release/        (git 제외) make_patcher.py 가 만드는 배포 폴더·ZIP
extract/ build/ (git 제외) 원본 추출본·빌드 결과
```

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드, 한국어 번역문, 문서: [MIT License](LICENSE) (© 2026 arqhive).
- 글꼴(글자 그림으로만 들어가며 글꼴 파일은 배포하지 않음)
  - 자막·대사: 본고딕 (Noto Sans KR, OFL)
  - 그림 글씨: 연천 허목체 (연천군), 나눔손글씨 펜 (네이버, OFL), 본명조·본고딕 (OFL), 송명 (OFL), 갈무리 (OFL)

## 면책

비공식 팬 번역이며 Nintendo, Silicon Knights와 관련이 없습니다. 「이터널 다크니스」 관련 상표·저작권은 각 권리자에게 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.

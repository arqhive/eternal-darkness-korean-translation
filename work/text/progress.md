# 번역 진행 기록

- 작업 묶음: work/text/chunks/001~285 (tools/make_chunks.py), 결과: work/text/ko/NNN_이름.json
- 완료: 000_pilot(견본 56줄, 승인)

## 완료 묶음
001~285 전부 완료(10/1). 3,335단위 중 3,333 번역 + 원문 유지 2(skip.json). (212~225 방 문구, 226~233 NPC, 234~257 아이템·주문, 258~265 책 메뉴, 266~269 버튼, 270~283 부검 기록, 284~285 메모리 카드. 001~211 컷신·실시간·음성 자막 전부. 201~211은 201_sub_voice 파일 하나) (048~091 엔딩은 048_ending 파일 하나, 092~135 정신 이상은 092_Insanity_1 파일 하나)

## 새 용어(용어집에 없던 것, 정한 표기)
- Centurion 백인대장 / Dead God 죽은 신 / Chapter Complete 「챕터　종료」(전각 공백) / 장 제목은 영어 챕터명 번역: The Chosen One 선택받은 자, The Binding of the Corpse God 시체의 신의 봉인, Suspicions of Conspiracy 음모의 의혹, The Gift of Forever 영원의 선물, The Lurking Horror 도사린 공포, A Journey into Darkness 어둠 속으로의 여정, Heresy! 이단이다!, The Forbidden City 금단의 도시, A Legacy of Darkness 어둠의 유산, A War to End All Wars 모든 전쟁을 끝내기 위한 전쟁, Ashes to Ashes 재는 재로
- Pillar of Flesh 살의 기둥 / Keeper (of the Ancients) 수호자 / Absent Horror 부재하는 공포 / master of the planes 차원의 지배자 / Power of the Planes 차원의 힘
- Ruins of Ehn'Gha 엔가의 폐허 / Scourge of God 신의 채찍 / Greater Guardian 위대한 가디언 / planetary alignment 행성들이 일렬로 늘어설 때 / Somme 솜 전투
- Gathering of Light 「빛이 모이는 곳」 / Hand of Jude 「유다의 손」 / Oublie Cathedral 우블리에 대성당 / Bell Tower 종탑 / Old Tower 옛 탑 / Brother Andrew 앤드루 수사 / Paul Augustine(1983) 폴 오거스틴
- 제목 줄의 시대·장소: 일본어판 형식(「기원전 26년　고대 페르시아」, 전각 공백 유지)

- 방·아이템(10/1): Urn 단지 / Effigy 조각상 / Statuette 작은 조각상 / Codex 석판 / Naga 나가 / Custodian 관리인 / Phillippe Augustine 필리프 오거스틴 주교 / Binding hall 봉인의 방 / Day·Night·Dawn·Dusk of Humanity 인류의 낮·밤·새벽·황혼 / Power Rune 힘의 룬 / Monument 기념비 / captor 붙잡아 둔 자 / Gun Cabinet 총기 진열장 / Pulp Novel 삼류 소설 / Message Tube 전갈 통 / Spice Jar 향신료 병 / Flash Powder 섬광 가루, Flash Pan 플래시 팬 / OICW Grenades OICW 유탄 / Book of Reliquaries 성유물의 책 / Memoires 회고록 / Note 쪽지
- Codex(아이템) 코덱스(방 문구의 stone tablet은 석판) / Guardian of Light 빛의 수호자 / Bonethief 본시프 / Junction Room 분기실 / Sacrificial Knife 제물용 칼 / Meditation Rod 명상 지팡이 / Talisman 탈리스만 / Gold Amulet 금 부적 / Message Scroll 전갈 두루마리 / Protect Area 프로텍트 에어리어(영어판 이름) / Mike·Michael은 모두 마이클(용어집)
- 고대신 정수 아이템(sys4)은 일본어판처럼 이름을 글자로 씀(~c 변수 대신 차투르가 등)

## 판단 메모
- 사용 한글 글자 1,003자(전체 번역 기준, 10/1) → 1~6번 장 1,536칸 안에 들어감 → 8번째 장 불필요(폰트 방침대로)
- 영상 다시 보기 제목(259)·부검 이름(258)은 영어판 순서가 일본판과 어긋나 일본판 구성(인물 Act 번호+제목)을 따름. 영어 제목이 같은 장면이면 영어 제목을 씀
- 메모리 카드(284~285)는 일본판 줄 구성·태그·존대를 따름. 게임 이름은 「이터널 다크니스」(일본 부제 招かれた13人 생략)
- 버튼(267~269)은 일본판 문자열의 태그 뼈대를 그대로 두고 일본어만 바꿈. 금고(SAFE) 줄은 아이콘 아래 간격이 한글 폭과 어긋날 수 있음 → 실행 검수 때 확인
- 일본어판 문장이 깨진(다른 글꼴 배치) 칸, 영어판에 없는 일본어 전용 문구(성유물의 책)는 일본어를 옮김
- 높임 재점검(10/1): 검사기가 일본어 반말을 だ·よ 등으로 끝날 때만 잡던 빈틈 확인 → 일본어 반말 서술로 끝나는 2줄 수정(190 XEL1_wanes·The_power_of, 016 ELLIA_under_a_reign). でした를 존대 표지에 추가
- 일본어 반말 명령형(「～ないで！」)은 앞뒤가 존대여도 반말로 옮김(10/1 사용자 결정): 016 ELLIA_Do_not_touch 「심장에 손대지 마!」, 042 MIKE_Dont_open_it 「여기서 열지 마!」
- 아이템 설명(item_desc)은 일본어판 형식: 첫 줄 이름(색 태그) + 본문. 수동 줄바꿈(602px)
- 시스템 묶음 #2 변형(글꼴 배치가 다른 묶음의 같은 문구)은 #1과 같은 번역
- 선택지 간격: 일본어판이 전각 공백이면 전각(「아니요　\i21　　예　\i20」), 반각이면 반각
- 실시간 자막(rt_sub, 시스템 9번 블록) 한계 590px은 일본어 원문 최대치 가안 → 줄이느라 번역이 짧아짐. in-engine 컷신 자막과 같은 창(765px·두 줄)일 가능성 큼 → 다음 측정판에서 확인하고, 넓으면 줄인 줄을 되살릴 것
- Act39 엔딩 알렉스의 「To think that once I could not see…」는 Act02 리치 대사의 반복 → 같은 표현 유지
- 검사기 보강: ~니다는 ㅂ받침만 존대, 끝 호칭 떼기(한·일), 문장부호로 안 끝나는 조각 줄은 높임 판정 생략
- 일본어판 칸이 영어 한 줄을 둘로 나누면 영어 내용을 두 칸에 나눠 담음(예 Act03 Face me…)
- 서술어 없는 부르는 말(존칭) 줄은 주변 높임을 따름 → work/text/check_exceptions.txt

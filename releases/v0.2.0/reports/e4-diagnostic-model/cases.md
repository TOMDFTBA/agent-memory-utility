# E4代表性案例

每组每场景按稳定snapshot ID取前两例，避免按事后最大差距选例。

## e3_posthoc / complementarity / s-2b6334d33548

问题：What is the six-digit access code for Locker-X48fc0dfe?；答案：880106。
支持集合：[['m-27ca54631c0f', 'm-5891834a4270']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-a7e1a84e2efa | 59 | 0.1267 | 0.0000 | The maintenance ticket for Locker-X48fc0dfe is 70793. The facilities clerk recorded this entry during a routine inventory review. |
| m-27ca54631c0f | 62 | 0.1999 | 0.5000 | The first three digits of the six-digit access code for Locker-X48fc0dfe are 880. This record was transcribed from the local register. |
| m-5891834a4270 | 63 | 0.3412 | 0.5000 | The last three digits of the six-digit access code for Locker-X48fc0dfe are 106. This record was transcribed from the local register. |
| m-b67bf4173d18 | 56 | -0.0700 | 0.0000 | The inventory label for Locker-X48fc0dfe is 26455. This record was transcribed from the local register. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-27ca54631c0f'] | 62 | 0.0000 |
| ['m-5891834a4270'] | 63 | 0.0000 |
| ['m-a7e1a84e2efa'] | 59 | 0.0000 |
| ['m-b67bf4173d18'] | 56 | 0.0000 |
| ['m-27ca54631c0f', 'm-5891834a4270'] | 125 | 0.5000 |
| ['m-27ca54631c0f', 'm-a7e1a84e2efa'] | 121 | 0.0000 |
| ['m-27ca54631c0f', 'm-b67bf4173d18'] | 118 | 0.0000 |
| ['m-5891834a4270', 'm-a7e1a84e2efa'] | 122 | 0.0000 |
| ['m-5891834a4270', 'm-b67bf4173d18'] | 119 | 0.0000 |
| ['m-a7e1a84e2efa', 'm-b67bf4173d18'] | 115 | 0.0000 |
| ['m-27ca54631c0f', 'm-5891834a4270', 'm-a7e1a84e2efa'] | 184 | 0.5000 |
| ['m-27ca54631c0f', 'm-5891834a4270', 'm-b67bf4173d18'] | 181 | 0.5000 |
| ['m-27ca54631c0f', 'm-a7e1a84e2efa', 'm-b67bf4173d18'] | 177 | 0.0000 |
| ['m-5891834a4270', 'm-a7e1a84e2efa', 'm-b67bf4173d18'] | 178 | 0.0000 |
| ['m-27ca54631c0f', 'm-5891834a4270', 'm-a7e1a84e2efa', 'm-b67bf4173d18'] | 240 | 0.5000 |

## e3_posthoc / complementarity / s-98cad688685a

问题：What is the six-digit access code for Cabinet-Xeb21b7ff?；答案：642949。
支持集合：[['m-5343b490f85a', 'm-64ff7555c346']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-803aa91eb520 | 45 | -0.0150 | 0.5000 | The inventory label for Cabinet-Xeb21b7ff is 11468. |
| m-5343b490f85a | 53 | 0.3021 | 1.0000 | The first three digits of the six-digit access code for Cabinet-Xeb21b7ff are 642. |
| m-64ff7555c346 | 61 | 0.3736 | 1.0000 | The last three digits of the six-digit access code for Cabinet-Xeb21b7ff are 949. This record was transcribed from the local register. |
| m-30bd28d00a7c | 55 | 0.2004 | 0.0000 | The maintenance ticket for Cabinet-Xeb21b7ff is 15415. This record was transcribed from the local register. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-30bd28d00a7c'] | 55 | 0.0000 |
| ['m-5343b490f85a'] | 53 | 0.0000 |
| ['m-64ff7555c346'] | 61 | 0.0000 |
| ['m-803aa91eb520'] | 45 | 0.0000 |
| ['m-30bd28d00a7c', 'm-5343b490f85a'] | 108 | 0.0000 |
| ['m-30bd28d00a7c', 'm-64ff7555c346'] | 116 | 0.0000 |
| ['m-30bd28d00a7c', 'm-803aa91eb520'] | 100 | 0.0000 |
| ['m-5343b490f85a', 'm-64ff7555c346'] | 114 | 1.0000 |
| ['m-5343b490f85a', 'm-803aa91eb520'] | 98 | 0.0000 |
| ['m-64ff7555c346', 'm-803aa91eb520'] | 106 | 0.0000 |
| ['m-30bd28d00a7c', 'm-5343b490f85a', 'm-64ff7555c346'] | 169 | 0.5000 |
| ['m-30bd28d00a7c', 'm-5343b490f85a', 'm-803aa91eb520'] | 153 | 0.0000 |
| ['m-30bd28d00a7c', 'm-64ff7555c346', 'm-803aa91eb520'] | 161 | 0.0000 |
| ['m-5343b490f85a', 'm-64ff7555c346', 'm-803aa91eb520'] | 159 | 1.0000 |
| ['m-30bd28d00a7c', 'm-5343b490f85a', 'm-64ff7555c346', 'm-803aa91eb520'] | 214 | 1.0000 |

## e3_posthoc / frequent_but_useless / s-1de27aac86dc

问题：What is the six-digit access code for Cabinet-X44df99fa?；答案：194274。
支持集合：[['m-33303e8f15f5']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-c609e2e07a6a | 57 | -0.0972 | 0.0000 | The service desk reference for Cabinet-X44df99fa is 98669. This record was transcribed from the local register. |
| m-33303e8f15f5 | 61 | 0.3799 | 1.0000 | Cabinet-X44df99fa opens with access code 194274. The facilities clerk recorded this entry during a routine inventory review. |
| m-138ed9dabaad | 52 | 0.0803 | 0.0000 | The maintenance ticket for Cabinet-X44df99fa is 80133. This record was transcribed from the local register. |
| m-b3d069e26a26 | 56 | 0.1488 | 0.0000 | The inventory label for Cabinet-X44df99fa is 44210. This record was transcribed from the local register. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-138ed9dabaad'] | 52 | 0.0000 |
| ['m-33303e8f15f5'] | 61 | 1.0000 |
| ['m-b3d069e26a26'] | 56 | 0.0000 |
| ['m-c609e2e07a6a'] | 57 | 0.0000 |
| ['m-138ed9dabaad', 'm-33303e8f15f5'] | 113 | 1.0000 |
| ['m-138ed9dabaad', 'm-b3d069e26a26'] | 108 | 0.0000 |
| ['m-138ed9dabaad', 'm-c609e2e07a6a'] | 109 | 0.0000 |
| ['m-33303e8f15f5', 'm-b3d069e26a26'] | 117 | 1.0000 |
| ['m-33303e8f15f5', 'm-c609e2e07a6a'] | 118 | 1.0000 |
| ['m-b3d069e26a26', 'm-c609e2e07a6a'] | 113 | 0.0000 |
| ['m-138ed9dabaad', 'm-33303e8f15f5', 'm-b3d069e26a26'] | 169 | 1.0000 |
| ['m-138ed9dabaad', 'm-33303e8f15f5', 'm-c609e2e07a6a'] | 170 | 1.0000 |
| ['m-138ed9dabaad', 'm-b3d069e26a26', 'm-c609e2e07a6a'] | 165 | 0.0000 |
| ['m-33303e8f15f5', 'm-b3d069e26a26', 'm-c609e2e07a6a'] | 174 | 1.0000 |
| ['m-138ed9dabaad', 'm-33303e8f15f5', 'm-b3d069e26a26', 'm-c609e2e07a6a'] | 226 | 1.0000 |

## e3_posthoc / frequent_but_useless / s-3f0e4b88d23e

问题：What is the six-digit access code for Cabinet-X92bf5151?；答案：620278。
支持集合：[['m-6b1d980aeb22']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-6b1d980aeb22 | 48 | 0.1595 | 1.0000 | The access code for Cabinet-X92bf5151 is 620278. |
| m-f295f537f8f9 | 49 | -0.1708 | 0.0000 | The service desk reference for Cabinet-X92bf5151 is 66736. |
| m-f34fdcd14590 | 46 | 0.1208 | 0.0000 | The maintenance ticket for Cabinet-X92bf5151 is 50042. |
| m-303596f47ccb | 59 | 0.3357 | 0.0000 | The inventory label for Cabinet-X92bf5151 is 11767. The facilities clerk recorded this entry during a routine inventory review. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-303596f47ccb'] | 59 | 0.0000 |
| ['m-6b1d980aeb22'] | 48 | 1.0000 |
| ['m-f295f537f8f9'] | 49 | 0.0000 |
| ['m-f34fdcd14590'] | 46 | 0.0000 |
| ['m-303596f47ccb', 'm-6b1d980aeb22'] | 107 | 1.0000 |
| ['m-303596f47ccb', 'm-f295f537f8f9'] | 108 | 0.0000 |
| ['m-303596f47ccb', 'm-f34fdcd14590'] | 105 | 0.0000 |
| ['m-6b1d980aeb22', 'm-f295f537f8f9'] | 97 | 1.0000 |
| ['m-6b1d980aeb22', 'm-f34fdcd14590'] | 94 | 1.0000 |
| ['m-f295f537f8f9', 'm-f34fdcd14590'] | 95 | 0.0000 |
| ['m-303596f47ccb', 'm-6b1d980aeb22', 'm-f295f537f8f9'] | 156 | 1.0000 |
| ['m-303596f47ccb', 'm-6b1d980aeb22', 'm-f34fdcd14590'] | 153 | 1.0000 |
| ['m-303596f47ccb', 'm-f295f537f8f9', 'm-f34fdcd14590'] | 154 | 0.0000 |
| ['m-6b1d980aeb22', 'm-f295f537f8f9', 'm-f34fdcd14590'] | 143 | 1.0000 |
| ['m-303596f47ccb', 'm-6b1d980aeb22', 'm-f295f537f8f9', 'm-f34fdcd14590'] | 202 | 1.0000 |

## e3_posthoc / old_but_useful / s-5b26c81cced9

问题：What is the six-digit access code for Locker-X118dee89?；答案：588908。
支持集合：[['m-84b7b6e7f34b']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-84b7b6e7f34b | 51 | 0.4355 | 1.0000 | Use 588908 as the access code to open Locker-X118dee89. |
| m-eab5cf353e98 | 56 | 0.2173 | 0.0000 | The service desk reference for Locker-X118dee89 is 47822. This record was transcribed from the local register. |
| m-ff4de83bc199 | 45 | -0.1301 | 0.0000 | The inventory label for Locker-X118dee89 is 24139. |
| m-2c8d8e336aef | 56 | 0.1376 | 0.0000 | The maintenance ticket for Locker-X118dee89 is 27653. This record was transcribed from the local register. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-2c8d8e336aef'] | 56 | 0.0000 |
| ['m-84b7b6e7f34b'] | 51 | 1.0000 |
| ['m-eab5cf353e98'] | 56 | 0.0000 |
| ['m-ff4de83bc199'] | 45 | 0.0000 |
| ['m-2c8d8e336aef', 'm-84b7b6e7f34b'] | 107 | 1.0000 |
| ['m-2c8d8e336aef', 'm-eab5cf353e98'] | 112 | 0.0000 |
| ['m-2c8d8e336aef', 'm-ff4de83bc199'] | 101 | 0.0000 |
| ['m-84b7b6e7f34b', 'm-eab5cf353e98'] | 107 | 1.0000 |
| ['m-84b7b6e7f34b', 'm-ff4de83bc199'] | 96 | 1.0000 |
| ['m-eab5cf353e98', 'm-ff4de83bc199'] | 101 | 0.0000 |
| ['m-2c8d8e336aef', 'm-84b7b6e7f34b', 'm-eab5cf353e98'] | 163 | 1.0000 |
| ['m-2c8d8e336aef', 'm-84b7b6e7f34b', 'm-ff4de83bc199'] | 152 | 1.0000 |
| ['m-2c8d8e336aef', 'm-eab5cf353e98', 'm-ff4de83bc199'] | 157 | 0.0000 |
| ['m-84b7b6e7f34b', 'm-eab5cf353e98', 'm-ff4de83bc199'] | 152 | 1.0000 |
| ['m-2c8d8e336aef', 'm-84b7b6e7f34b', 'm-eab5cf353e98', 'm-ff4de83bc199'] | 208 | 1.0000 |

## e3_posthoc / old_but_useful / s-700a78e631af

问题：What is the six-digit access code for Locker-X1d4bd955?；答案：593462。
支持集合：[['m-245a5e5d3e0f']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-245a5e5d3e0f | 64 | 0.2947 | 1.0000 | Use 593462 as the access code to open Locker-X1d4bd955. The facilities clerk recorded this entry during a routine inventory review. |
| m-2955928fba80 | 61 | 0.1129 | 0.0000 | The service desk reference for Locker-X1d4bd955 is 94546. The facilities clerk recorded this entry during a routine inventory review. |
| m-e28a549b2563 | 49 | 0.1234 | 0.0000 | The maintenance ticket for Locker-X1d4bd955 is 54199. |
| m-f132bb55777a | 57 | -0.0867 | 0.0000 | The inventory label for Locker-X1d4bd955 is 37855. This record was transcribed from the local register. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-245a5e5d3e0f'] | 64 | 1.0000 |
| ['m-2955928fba80'] | 61 | 0.0000 |
| ['m-e28a549b2563'] | 49 | 0.0000 |
| ['m-f132bb55777a'] | 57 | 0.0000 |
| ['m-245a5e5d3e0f', 'm-2955928fba80'] | 125 | 1.0000 |
| ['m-245a5e5d3e0f', 'm-e28a549b2563'] | 113 | 1.0000 |
| ['m-245a5e5d3e0f', 'm-f132bb55777a'] | 121 | 1.0000 |
| ['m-2955928fba80', 'm-e28a549b2563'] | 110 | 0.0000 |
| ['m-2955928fba80', 'm-f132bb55777a'] | 118 | 0.0000 |
| ['m-e28a549b2563', 'm-f132bb55777a'] | 106 | 0.0000 |
| ['m-245a5e5d3e0f', 'm-2955928fba80', 'm-e28a549b2563'] | 174 | 1.0000 |
| ['m-245a5e5d3e0f', 'm-2955928fba80', 'm-f132bb55777a'] | 182 | 1.0000 |
| ['m-245a5e5d3e0f', 'm-e28a549b2563', 'm-f132bb55777a'] | 170 | 1.0000 |
| ['m-2955928fba80', 'm-e28a549b2563', 'm-f132bb55777a'] | 167 | 0.0000 |
| ['m-245a5e5d3e0f', 'm-2955928fba80', 'm-e28a549b2563', 'm-f132bb55777a'] | 231 | 1.0000 |

## e3_posthoc / redundancy / s-0ffd5159ac64

问题：What is the six-digit access code for Locker-X2e3cf82e?；答案：284267。
支持集合：[['m-aeb2d7ee7429'], ['m-5a6ed297191a']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-aeb2d7ee7429 | 59 | 0.4607 | 0.0000 | Use 284267 as the access code to open Locker-X2e3cf82e. This record was transcribed from the local register. |
| m-19fa297e16ef | 47 | 0.1933 | 0.0000 | The maintenance ticket for Locker-X2e3cf82e is 21822. |
| m-d72084674691 | 61 | -0.0421 | 0.0000 | The inventory label for Locker-X2e3cf82e is 41182. The facilities clerk recorded this entry during a routine inventory review. |
| m-5a6ed297191a | 63 | 0.1364 | 0.0000 | To open Locker-X2e3cf82e, enter the access code 284267. The facilities clerk recorded this entry during a routine inventory review. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-19fa297e16ef'] | 47 | 0.0000 |
| ['m-5a6ed297191a'] | 63 | 1.0000 |
| ['m-aeb2d7ee7429'] | 59 | 1.0000 |
| ['m-d72084674691'] | 61 | 0.0000 |
| ['m-19fa297e16ef', 'm-5a6ed297191a'] | 110 | 1.0000 |
| ['m-19fa297e16ef', 'm-aeb2d7ee7429'] | 106 | 1.0000 |
| ['m-19fa297e16ef', 'm-d72084674691'] | 108 | 0.0000 |
| ['m-5a6ed297191a', 'm-aeb2d7ee7429'] | 122 | 1.0000 |
| ['m-5a6ed297191a', 'm-d72084674691'] | 124 | 1.0000 |
| ['m-aeb2d7ee7429', 'm-d72084674691'] | 120 | 1.0000 |
| ['m-19fa297e16ef', 'm-5a6ed297191a', 'm-aeb2d7ee7429'] | 169 | 1.0000 |
| ['m-19fa297e16ef', 'm-5a6ed297191a', 'm-d72084674691'] | 171 | 1.0000 |
| ['m-19fa297e16ef', 'm-aeb2d7ee7429', 'm-d72084674691'] | 167 | 1.0000 |
| ['m-5a6ed297191a', 'm-aeb2d7ee7429', 'm-d72084674691'] | 183 | 1.0000 |
| ['m-19fa297e16ef', 'm-5a6ed297191a', 'm-aeb2d7ee7429', 'm-d72084674691'] | 230 | 1.0000 |

## e3_posthoc / redundancy / s-2b4f98ab8742

问题：What is the six-digit access code for Locker-X66daed3c?；答案：613759。
支持集合：[['m-eb32d966f53a'], ['m-bd4b62801ebf']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-7556831cc319 | 47 | 0.0115 | 0.0000 | The inventory label for Locker-X66daed3c is 54438. |
| m-bd4b62801ebf | 61 | 0.2573 | 0.0000 | To open Locker-X66daed3c, enter the access code 613759. The facilities clerk recorded this entry during a routine inventory review. |
| m-922f4f2301f6 | 60 | 0.2034 | 0.0000 | The maintenance ticket for Locker-X66daed3c is 50702. The facilities clerk recorded this entry during a routine inventory review. |
| m-eb32d966f53a | 48 | 0.3691 | 0.0000 | The access code for Locker-X66daed3c is 613759. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-7556831cc319'] | 47 | 0.0000 |
| ['m-922f4f2301f6'] | 60 | 0.0000 |
| ['m-bd4b62801ebf'] | 61 | 1.0000 |
| ['m-eb32d966f53a'] | 48 | 1.0000 |
| ['m-7556831cc319', 'm-922f4f2301f6'] | 107 | 0.0000 |
| ['m-7556831cc319', 'm-bd4b62801ebf'] | 108 | 1.0000 |
| ['m-7556831cc319', 'm-eb32d966f53a'] | 95 | 1.0000 |
| ['m-922f4f2301f6', 'm-bd4b62801ebf'] | 121 | 1.0000 |
| ['m-922f4f2301f6', 'm-eb32d966f53a'] | 108 | 1.0000 |
| ['m-bd4b62801ebf', 'm-eb32d966f53a'] | 109 | 1.0000 |
| ['m-7556831cc319', 'm-922f4f2301f6', 'm-bd4b62801ebf'] | 168 | 1.0000 |
| ['m-7556831cc319', 'm-922f4f2301f6', 'm-eb32d966f53a'] | 155 | 1.0000 |
| ['m-7556831cc319', 'm-bd4b62801ebf', 'm-eb32d966f53a'] | 156 | 1.0000 |
| ['m-922f4f2301f6', 'm-bd4b62801ebf', 'm-eb32d966f53a'] | 169 | 1.0000 |
| ['m-7556831cc319', 'm-922f4f2301f6', 'm-bd4b62801ebf', 'm-eb32d966f53a'] | 216 | 1.0000 |

## e4_independent / complementarity / s-1f9fccc73e42

问题：What is the six-digit access code for Locker-Xd8ceced4?；答案：105148。
支持集合：[['m-12070c27e428', 'm-8eb23e739bfe']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-8eb23e739bfe | 60 | 0.2955 | 0.0000 | The last three digits of the six-digit access code for Locker-Xd8ceced4 are 148. This record was transcribed from the local register. |
| m-411a4d8d2766 | 56 | 0.0590 | 0.0000 | The inventory label for Locker-Xd8ceced4 is 59302. This record was transcribed from the local register. |
| m-c733a96a3121 | 59 | 0.2002 | 0.0000 | The maintenance ticket for Locker-Xd8ceced4 is 75137. The facilities clerk recorded this entry during a routine inventory review. |
| m-12070c27e428 | 62 | 0.2792 | 0.0000 | The first three digits of the six-digit access code for Locker-Xd8ceced4 are 105. This record was transcribed from the local register. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-12070c27e428'] | 62 | 0.0000 |
| ['m-411a4d8d2766'] | 56 | 0.0000 |
| ['m-8eb23e739bfe'] | 60 | 0.0000 |
| ['m-c733a96a3121'] | 59 | 0.0000 |
| ['m-12070c27e428', 'm-411a4d8d2766'] | 118 | 0.0000 |
| ['m-12070c27e428', 'm-8eb23e739bfe'] | 122 | 0.0000 |
| ['m-12070c27e428', 'm-c733a96a3121'] | 121 | 0.0000 |
| ['m-411a4d8d2766', 'm-8eb23e739bfe'] | 116 | 0.0000 |
| ['m-411a4d8d2766', 'm-c733a96a3121'] | 115 | 0.0000 |
| ['m-8eb23e739bfe', 'm-c733a96a3121'] | 119 | 0.0000 |
| ['m-12070c27e428', 'm-411a4d8d2766', 'm-8eb23e739bfe'] | 178 | 0.0000 |
| ['m-12070c27e428', 'm-411a4d8d2766', 'm-c733a96a3121'] | 177 | 0.0000 |
| ['m-12070c27e428', 'm-8eb23e739bfe', 'm-c733a96a3121'] | 181 | 0.0000 |
| ['m-411a4d8d2766', 'm-8eb23e739bfe', 'm-c733a96a3121'] | 175 | 0.0000 |
| ['m-12070c27e428', 'm-411a4d8d2766', 'm-8eb23e739bfe', 'm-c733a96a3121'] | 237 | 0.0000 |

## e4_independent / complementarity / s-2e88e7834598

问题：What is the six-digit access code for Vault-Xc58f2ab8?；答案：883781。
支持集合：[['m-9b2eee0dfa02', 'm-7d312ff663e2']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-9b2eee0dfa02 | 51 | 0.3469 | 0.5000 | The first three digits of the six-digit access code for Vault-Xc58f2ab8 are 883. |
| m-7d312ff663e2 | 65 | 0.3820 | 0.5000 | The last three digits of the six-digit access code for Vault-Xc58f2ab8 are 781. The facilities clerk recorded this entry during a routine inventory review. |
| m-31988cc9726a | 56 | 0.2392 | 0.0000 | The maintenance ticket for Vault-Xc58f2ab8 is 81748. This record was transcribed from the local register. |
| m-97f0b4ee4d47 | 47 | -0.0910 | 0.0000 | The inventory label for Vault-Xc58f2ab8 is 27178. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-31988cc9726a'] | 56 | 0.0000 |
| ['m-7d312ff663e2'] | 65 | 0.0000 |
| ['m-97f0b4ee4d47'] | 47 | 0.0000 |
| ['m-9b2eee0dfa02'] | 51 | 0.0000 |
| ['m-31988cc9726a', 'm-7d312ff663e2'] | 121 | 0.0000 |
| ['m-31988cc9726a', 'm-97f0b4ee4d47'] | 103 | 0.0000 |
| ['m-31988cc9726a', 'm-9b2eee0dfa02'] | 107 | 0.0000 |
| ['m-7d312ff663e2', 'm-97f0b4ee4d47'] | 112 | 0.0000 |
| ['m-7d312ff663e2', 'm-9b2eee0dfa02'] | 116 | 1.0000 |
| ['m-97f0b4ee4d47', 'm-9b2eee0dfa02'] | 98 | 0.0000 |
| ['m-31988cc9726a', 'm-7d312ff663e2', 'm-97f0b4ee4d47'] | 168 | 0.0000 |
| ['m-31988cc9726a', 'm-7d312ff663e2', 'm-9b2eee0dfa02'] | 172 | 0.5000 |
| ['m-31988cc9726a', 'm-97f0b4ee4d47', 'm-9b2eee0dfa02'] | 154 | 0.0000 |
| ['m-7d312ff663e2', 'm-97f0b4ee4d47', 'm-9b2eee0dfa02'] | 163 | 0.5000 |
| ['m-31988cc9726a', 'm-7d312ff663e2', 'm-97f0b4ee4d47', 'm-9b2eee0dfa02'] | 219 | 0.5000 |

## e4_independent / frequent_but_useless / s-291728e71d6c

问题：What is the six-digit access code for Vault-Xb3eb36a3?；答案：632954。
支持集合：[['m-26261180fc82']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-09789b3527ce | 57 | -0.1680 | 0.0000 | The service desk reference for Vault-Xb3eb36a3 is 86152. This record was transcribed from the local register. |
| m-4a112ba6bcca | 57 | 0.1044 | 0.0000 | The maintenance ticket for Vault-Xb3eb36a3 is 28409. The facilities clerk recorded this entry during a routine inventory review. |
| m-26261180fc82 | 62 | 0.3897 | 1.0000 | Use 632954 as the access code to open Vault-Xb3eb36a3. The facilities clerk recorded this entry during a routine inventory review. |
| m-62135bfabffe | 56 | 0.0998 | 0.0000 | The inventory label for Vault-Xb3eb36a3 is 25325. The facilities clerk recorded this entry during a routine inventory review. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-09789b3527ce'] | 57 | 0.0000 |
| ['m-26261180fc82'] | 62 | 1.0000 |
| ['m-4a112ba6bcca'] | 57 | 0.0000 |
| ['m-62135bfabffe'] | 56 | 0.0000 |
| ['m-09789b3527ce', 'm-26261180fc82'] | 119 | 1.0000 |
| ['m-09789b3527ce', 'm-4a112ba6bcca'] | 114 | 0.0000 |
| ['m-09789b3527ce', 'm-62135bfabffe'] | 113 | 0.0000 |
| ['m-26261180fc82', 'm-4a112ba6bcca'] | 119 | 1.0000 |
| ['m-26261180fc82', 'm-62135bfabffe'] | 118 | 1.0000 |
| ['m-4a112ba6bcca', 'm-62135bfabffe'] | 113 | 0.0000 |
| ['m-09789b3527ce', 'm-26261180fc82', 'm-4a112ba6bcca'] | 176 | 1.0000 |
| ['m-09789b3527ce', 'm-26261180fc82', 'm-62135bfabffe'] | 175 | 1.0000 |
| ['m-09789b3527ce', 'm-4a112ba6bcca', 'm-62135bfabffe'] | 170 | 0.0000 |
| ['m-26261180fc82', 'm-4a112ba6bcca', 'm-62135bfabffe'] | 175 | 1.0000 |
| ['m-09789b3527ce', 'm-26261180fc82', 'm-4a112ba6bcca', 'm-62135bfabffe'] | 232 | 1.0000 |

## e4_independent / frequent_but_useless / s-9bb9f2be062e

问题：What is the six-digit access code for Locker-X8367b786?；答案：921805。
支持集合：[['m-d7b88a8feb2a']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-aa65c0a3bac0 | 59 | 0.2271 | 0.0000 | The inventory label for Locker-X8367b786 is 86411. The facilities clerk recorded this entry during a routine inventory review. |
| m-65a9694bf182 | 58 | 0.1081 | 0.0000 | The maintenance ticket for Locker-X8367b786 is 22497. This record was transcribed from the local register. |
| m-0b8b5160836b | 51 | -0.2474 | 0.0000 | The service desk reference for Locker-X8367b786 is 31728. |
| m-d7b88a8feb2a | 61 | 0.3746 | 1.0000 | Locker-X8367b786 opens with access code 921805. The facilities clerk recorded this entry during a routine inventory review. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-0b8b5160836b'] | 51 | 0.0000 |
| ['m-65a9694bf182'] | 58 | 0.0000 |
| ['m-aa65c0a3bac0'] | 59 | 0.0000 |
| ['m-d7b88a8feb2a'] | 61 | 1.0000 |
| ['m-0b8b5160836b', 'm-65a9694bf182'] | 109 | 0.0000 |
| ['m-0b8b5160836b', 'm-aa65c0a3bac0'] | 110 | 0.0000 |
| ['m-0b8b5160836b', 'm-d7b88a8feb2a'] | 112 | 1.0000 |
| ['m-65a9694bf182', 'm-aa65c0a3bac0'] | 117 | 0.0000 |
| ['m-65a9694bf182', 'm-d7b88a8feb2a'] | 119 | 1.0000 |
| ['m-aa65c0a3bac0', 'm-d7b88a8feb2a'] | 120 | 1.0000 |
| ['m-0b8b5160836b', 'm-65a9694bf182', 'm-aa65c0a3bac0'] | 168 | 0.0000 |
| ['m-0b8b5160836b', 'm-65a9694bf182', 'm-d7b88a8feb2a'] | 170 | 1.0000 |
| ['m-0b8b5160836b', 'm-aa65c0a3bac0', 'm-d7b88a8feb2a'] | 171 | 1.0000 |
| ['m-65a9694bf182', 'm-aa65c0a3bac0', 'm-d7b88a8feb2a'] | 178 | 1.0000 |
| ['m-0b8b5160836b', 'm-65a9694bf182', 'm-aa65c0a3bac0', 'm-d7b88a8feb2a'] | 229 | 1.0000 |

## e4_independent / old_but_useful / s-16a70dcecf9b

问题：What is the six-digit access code for Cabinet-X3e4b654a?；答案：118817。
支持集合：[['m-71933d4a0be1']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-71933d4a0be1 | 49 | 0.3730 | 1.0000 | The access code for Cabinet-X3e4b654a is 118817. |
| m-6a1892794449 | 49 | -0.0045 | 0.0000 | The inventory label for Cabinet-X3e4b654a is 57677. |
| m-e986beaf8b06 | 47 | 0.2527 | 0.0000 | The maintenance ticket for Cabinet-X3e4b654a is 24099. |
| m-245d41e6fb8e | 61 | 0.1881 | 0.0000 | The service desk reference for Cabinet-X3e4b654a is 90031. The facilities clerk recorded this entry during a routine inventory review. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-245d41e6fb8e'] | 61 | 0.0000 |
| ['m-6a1892794449'] | 49 | 0.0000 |
| ['m-71933d4a0be1'] | 49 | 1.0000 |
| ['m-e986beaf8b06'] | 47 | 0.0000 |
| ['m-245d41e6fb8e', 'm-6a1892794449'] | 110 | 0.0000 |
| ['m-245d41e6fb8e', 'm-71933d4a0be1'] | 110 | 1.0000 |
| ['m-245d41e6fb8e', 'm-e986beaf8b06'] | 108 | 0.0000 |
| ['m-6a1892794449', 'm-71933d4a0be1'] | 98 | 1.0000 |
| ['m-6a1892794449', 'm-e986beaf8b06'] | 96 | 0.0000 |
| ['m-71933d4a0be1', 'm-e986beaf8b06'] | 96 | 1.0000 |
| ['m-245d41e6fb8e', 'm-6a1892794449', 'm-71933d4a0be1'] | 159 | 1.0000 |
| ['m-245d41e6fb8e', 'm-6a1892794449', 'm-e986beaf8b06'] | 157 | 0.0000 |
| ['m-245d41e6fb8e', 'm-71933d4a0be1', 'm-e986beaf8b06'] | 157 | 1.0000 |
| ['m-6a1892794449', 'm-71933d4a0be1', 'm-e986beaf8b06'] | 145 | 1.0000 |
| ['m-245d41e6fb8e', 'm-6a1892794449', 'm-71933d4a0be1', 'm-e986beaf8b06'] | 206 | 1.0000 |

## e4_independent / old_but_useful / s-35aa54c8bb37

问题：What is the six-digit access code for Cabinet-Xdb6c53e3?；答案：551878。
支持集合：[['m-e45ad5aee487']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-e45ad5aee487 | 57 | 0.4018 | 1.0000 | Cabinet-Xdb6c53e3 opens with access code 551878. This record was transcribed from the local register. |
| m-3a8471341b61 | 49 | 0.1823 | 0.0000 | The service desk reference for Cabinet-Xdb6c53e3 is 61620. |
| m-228af650a308 | 59 | 0.1204 | 0.0000 | The maintenance ticket for Cabinet-Xdb6c53e3 is 57275. The facilities clerk recorded this entry during a routine inventory review. |
| m-c5ec7f17b4c6 | 47 | -0.1164 | 0.0000 | The inventory label for Cabinet-Xdb6c53e3 is 90145. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-228af650a308'] | 59 | 0.0000 |
| ['m-3a8471341b61'] | 49 | 0.0000 |
| ['m-c5ec7f17b4c6'] | 47 | 0.0000 |
| ['m-e45ad5aee487'] | 57 | 1.0000 |
| ['m-228af650a308', 'm-3a8471341b61'] | 108 | 0.0000 |
| ['m-228af650a308', 'm-c5ec7f17b4c6'] | 106 | 0.0000 |
| ['m-228af650a308', 'm-e45ad5aee487'] | 116 | 1.0000 |
| ['m-3a8471341b61', 'm-c5ec7f17b4c6'] | 96 | 0.0000 |
| ['m-3a8471341b61', 'm-e45ad5aee487'] | 106 | 1.0000 |
| ['m-c5ec7f17b4c6', 'm-e45ad5aee487'] | 104 | 1.0000 |
| ['m-228af650a308', 'm-3a8471341b61', 'm-c5ec7f17b4c6'] | 155 | 0.0000 |
| ['m-228af650a308', 'm-3a8471341b61', 'm-e45ad5aee487'] | 165 | 1.0000 |
| ['m-228af650a308', 'm-c5ec7f17b4c6', 'm-e45ad5aee487'] | 163 | 1.0000 |
| ['m-3a8471341b61', 'm-c5ec7f17b4c6', 'm-e45ad5aee487'] | 153 | 1.0000 |
| ['m-228af650a308', 'm-3a8471341b61', 'm-c5ec7f17b4c6', 'm-e45ad5aee487'] | 212 | 1.0000 |

## e4_independent / redundancy / s-1c870f772291

问题：What is the six-digit access code for Vault-X1295dc35?；答案：330751。
支持集合：[['m-a318755fda88'], ['m-732620087fa6']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-5574ab43f680 | 59 | 0.2449 | 0.0000 | The maintenance ticket for Vault-X1295dc35 is 63138. The facilities clerk recorded this entry during a routine inventory review. |
| m-d919f9ad9b76 | 56 | 0.0697 | 0.0000 | The inventory label for Vault-X1295dc35 is 98390. This record was transcribed from the local register. |
| m-a318755fda88 | 57 | 0.3482 | 0.0000 | The access code for Vault-X1295dc35 is 330751. This record was transcribed from the local register. |
| m-732620087fa6 | 62 | 0.2354 | 0.0000 | To open Vault-X1295dc35, enter the access code 330751. The facilities clerk recorded this entry during a routine inventory review. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-5574ab43f680'] | 59 | 0.0000 |
| ['m-732620087fa6'] | 62 | 1.0000 |
| ['m-a318755fda88'] | 57 | 1.0000 |
| ['m-d919f9ad9b76'] | 56 | 0.0000 |
| ['m-5574ab43f680', 'm-732620087fa6'] | 121 | 1.0000 |
| ['m-5574ab43f680', 'm-a318755fda88'] | 116 | 1.0000 |
| ['m-5574ab43f680', 'm-d919f9ad9b76'] | 115 | 0.0000 |
| ['m-732620087fa6', 'm-a318755fda88'] | 119 | 1.0000 |
| ['m-732620087fa6', 'm-d919f9ad9b76'] | 118 | 1.0000 |
| ['m-a318755fda88', 'm-d919f9ad9b76'] | 113 | 1.0000 |
| ['m-5574ab43f680', 'm-732620087fa6', 'm-a318755fda88'] | 178 | 1.0000 |
| ['m-5574ab43f680', 'm-732620087fa6', 'm-d919f9ad9b76'] | 177 | 1.0000 |
| ['m-5574ab43f680', 'm-a318755fda88', 'm-d919f9ad9b76'] | 172 | 1.0000 |
| ['m-732620087fa6', 'm-a318755fda88', 'm-d919f9ad9b76'] | 175 | 1.0000 |
| ['m-5574ab43f680', 'm-732620087fa6', 'm-a318755fda88', 'm-d919f9ad9b76'] | 234 | 1.0000 |

## e4_independent / redundancy / s-406dd6ee058a

问题：What is the six-digit access code for Locker-X07e3ea1d?；答案：209137。
支持集合：[['m-7157b7ec3168'], ['m-f722a6ca7ae3']]

| ID | tokens | predicted | LOO | 内容 |
|---|---:|---:|---:|---|
| m-43eda7d1493e | 47 | 0.3776 | 0.0000 | The maintenance ticket for Locker-X07e3ea1d is 29640. |
| m-7157b7ec3168 | 61 | 0.2697 | 0.0000 | The access code for Locker-X07e3ea1d is 209137. The facilities clerk recorded this entry during a routine inventory review. |
| m-974f53e5f049 | 61 | 0.0882 | 0.0000 | The inventory label for Locker-X07e3ea1d is 82798. The facilities clerk recorded this entry during a routine inventory review. |
| m-f722a6ca7ae3 | 62 | 0.2699 | 0.0000 | To open Locker-X07e3ea1d, enter the access code 209137. The facilities clerk recorded this entry during a routine inventory review. |

| 存储集合 | tokens | 窗口EM |
|---|---:|---:|
| [] | 0 | 0.0000 |
| ['m-43eda7d1493e'] | 47 | 0.0000 |
| ['m-7157b7ec3168'] | 61 | 1.0000 |
| ['m-974f53e5f049'] | 61 | 0.0000 |
| ['m-f722a6ca7ae3'] | 62 | 1.0000 |
| ['m-43eda7d1493e', 'm-7157b7ec3168'] | 108 | 1.0000 |
| ['m-43eda7d1493e', 'm-974f53e5f049'] | 108 | 0.0000 |
| ['m-43eda7d1493e', 'm-f722a6ca7ae3'] | 109 | 1.0000 |
| ['m-7157b7ec3168', 'm-974f53e5f049'] | 122 | 1.0000 |
| ['m-7157b7ec3168', 'm-f722a6ca7ae3'] | 123 | 1.0000 |
| ['m-974f53e5f049', 'm-f722a6ca7ae3'] | 123 | 1.0000 |
| ['m-43eda7d1493e', 'm-7157b7ec3168', 'm-974f53e5f049'] | 169 | 1.0000 |
| ['m-43eda7d1493e', 'm-7157b7ec3168', 'm-f722a6ca7ae3'] | 170 | 1.0000 |
| ['m-43eda7d1493e', 'm-974f53e5f049', 'm-f722a6ca7ae3'] | 170 | 1.0000 |
| ['m-7157b7ec3168', 'm-974f53e5f049', 'm-f722a6ca7ae3'] | 184 | 1.0000 |
| ['m-43eda7d1493e', 'm-7157b7ec3168', 'm-974f53e5f049', 'm-f722a6ca7ae3'] | 231 | 1.0000 |


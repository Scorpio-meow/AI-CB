from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)

try:
    from whoosh.analysis import StandardAnalyzer, Analyzer, Tokenizer, Token
    HAS_WHOOSH = True
except ImportError:
    HAS_WHOOSH = False
    Analyzer = object  # type: ignore
    Tokenizer = object  # type: ignore
    Token = None  # type: ignore
    StandardAnalyzer = None  # type: ignore

try:
    import jieba
    HAS_JIEBA = True
except Exception:
    HAS_JIEBA = False

if HAS_WHOOSH and HAS_JIEBA:
    class JiebaTokenizer(Tokenizer):
        def __call__(
            self,
            value,
            positions=False,
            chars=False,
            keeporiginal=False,
            removestops=False,
            start_pos=0,
            start_char=0,
            tokenize=True,
            mode="default",
            **kwargs
        ):
            t = Token(positions, chars, removestops=removestops)
            if not tokenize:
                return
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", "ignore")
                except Exception:
                    value = value.decode(errors="ignore")
            pos = start_pos
            char_pos = start_char
            for w in jieba.cut(value, cut_all=False):
                w = w.strip()
                if not w:
                    continue
                t.original = w
                t.text = w
                t.boost = 1.0
                if positions:
                    t.pos = pos
                    pos += 1
                if chars:
                    idx = value.find(w, char_pos)
                    if idx < 0:
                        idx = char_pos
                    t.startchar = idx
                    t.endchar = idx + len(w)
                    char_pos = t.endchar
                yield t

    class JiebaAnalyzer(Analyzer):
        def __init__(self):
            self._tokenizer = JiebaTokenizer()

        def __call__(self, value, **kwargs):
            return self._tokenizer(value, **kwargs)
else:
    JiebaTokenizer = None  # type: ignore
    JiebaAnalyzer = None  # type: ignore

DOMAIN_WORDS = [
    "補休", "到期", "遞延", "產檢", "育嬰留停", "免刷卡", "時刻維護", "集體異動", "調班",
    "外勤", "PAKKA", "MES", "薪資條", "在職證明", "眷屬", "健保", "勞保", "資遣",
    "特休", "颱風", "防災假", "逾期補登", "刷卡", "忘刷", "排班", "輪班", "四週彈性工時",
    "調班申請", "人事調閱", "加班", "請假", "同意書", "證明", "出勤管理", "差勤卡鐘",
    "門禁權限", "工時填寫", "留職停薪", "病假", "事假", "公假", "婚假", "喪假",
    "陪產假", "產假", "生理假", "家庭照顧假", "公傷假", "特別休假", "休假排休",
    "核心上班時間", "彈性上下班", "加班申請", "補休申請", "忘刷申請", "異常申請",
    "人員招募", "甄選", "任用", "面談紀錄", "試用考核", "新進人員", "輔導員",
    "內部轉調", "升遷", "調薪", "年度調薪", "離職", "自願離職", "非自願離職",
    "預告期間", "工作交接", "離職證明", "資遣費", "退休金", "勞退提撥", "委任經理人",
    "海外派駐", "派駐大陸", "組織異動", "部門異動", "職位異動", "職務代理人",
    "企業實習生", "工讀生", "約聘人員", "半導體專案", "專案人員", "研發替代役",
    "績效管理", "績效評核", "年中評核", "年底評核", "定期評核", "工作目標",
    "績效指標", "KPI", "部門績效", "個人績效", "績效回饋", "績效改善", "考績",
    "工作表現", "能力評估", "潛能發展", "職能發展", "改善計畫", "績效面談",
    "組織訓練", "部門訓練", "內部講師", "外部講師", "教育訓練", "訓練需求",
    "訓練計畫", "課程規劃", "在職訓練", "專業訓練", "技能訓練", "新人訓練",
    "線上訓練", "實體訓練", "教材開發", "訓練評估", "訓練紀錄", "訓練時數",
    "資格認證", "專業證照", "技術士", "技能檢定", "Microsoft認證", "Cisco認證",
    "Oracle認證", "IBM認證", "CMMI", "ISO認證",
    "薪資", "薪資條", "薪資轉帳", "薪轉帳戶", "扣繳憑單", "所得稅", "二代健保",
    "團體保險", "員工保險", "勞保", "健保", "團保", "意外險", "壽險", "退休金",
    "勞退", "舊制退休", "新制退休", "退休金提撥", "資深員工獎勵", "神通之星",
    "員工紅利", "績效獎金", "年終獎金", "三節獎金", "專案獎金",
    "員工獎懲", "嘉獎", "記功", "申誡", "記過", "懲處", "考核", "獎勵", "懲戒",
    "工作倫理", "紀律規範", "誠信經營", "利益衝突", "行為準則", "保密協定",
    "競業禁止", "智慧財產權", "營業秘密", "個人資料保護", "資訊安全",
    "職業安全", "職業衛生", "工作場所", "性騷擾防治", "申訴", "不法侵害",
    "異常工作負荷", "過勞防護", "輪班工作", "夜間工作", "長時間工作",
    "健康管理", "健康檢查", "職業病", "工作壓力", "身心健康", "臨場醫師",
    "健康諮詢", "風險評估", "預防措施",
    "組織架構", "組織層級", "事業群", "功能中心", "處級單位", "部級單位",
    "組級單位", "總經理", "副總經理", "協理", "資深協理", "處長", "經理",
    "資深經理", "副理", "課長", "組長", "主任", "專員", "資深專員", "工程師",
    "資深工程師", "主任工程師", "專案經理", "技術經理", "業務經理",
    "管理職", "專門職", "主管職", "非管理職", "職位設置", "職責",
    "專案管理", "專案執行", "專案支援", "內部支援", "產品研發", "研發補貼",
    "計價作業", "成本代碼", "預算編列", "預算控制", "人力預算", "員額編制",
    "專案人員", "安全評估", "專利提案", "專利申請", "專利獎勵", "專利維護",
    "系統整合", "軟體開發", "硬體維護", "網路架構", "資訊安全", "資通訊",
    "雲端服務", "物聯網", "AIoT", "智慧城市", "智慧交通", "數位轉型",
    "資料庫", "伺服器", "虛擬化", "備份還原", "版本控管", "建構管理",
    "驗證確認", "CMMI", "內部稽核", "品質保證", "流程改善",
    "神通資訊", "神通資科", "神通電腦", "聯華神通", "神耀科技", "艾迪訊",
    "MITAC", "MiTAC", "GHP", "單一入口網", "員工服務系統", "AVAYA",
    "教育訓練系統", "技能資料庫", "差勤系統", "簽核系統", "作業簽核",
    "勞動基準法", "勞基法", "就業服務法", "職業安全衛生法", "勞工健康保護",
    "性別工作平等法", "勞資會議", "工會", "團體協約", "勞動檢查", "勞資爭議",
    "職災", "職業災害", "工傷", "勞保給付", "失能給付", "死亡給付",
    "呈核", "簽核", "核決", "核准", "核定", "會簽", "知會", "副知", "抄送",
    "附件", "表單", "申請單", "同意書", "切結書", "聲明書", "承諾書",
    "作業程序", "管理辦法", "實施細則", "注意事項", "FAQ", "SOP",
    "允入準則", "允出準則", "控制重點", "調適原則", "版次", "修訂",
    "事業群主管", "直線主管", "部門主管", "單位主管", "權責主管",
    "承辦人", "窗口", "聯繫人", "負責人", "協辦人", "會辦人"
]


def init_domain_dictionary(data_dir: str = "data") -> None:
    if not HAS_JIEBA:
        return

    jieba_dict_path = os.path.join(data_dir, "jieba_dict.txt")
    if os.path.exists(jieba_dict_path):
        try:
            jieba.load_userdict(jieba_dict_path)
            logger.info(f"Jieba 自定義詞典已載入: {jieba_dict_path}")
        except Exception as e:
            logger.warning(f"Jieba 自定義詞典載入失敗: {e}")

    for w in DOMAIN_WORDS:
        try:
            jieba.add_word(w)
        except Exception:
            pass


def get_chinese_analyzer():
    if not HAS_WHOOSH:
        return None
    if HAS_JIEBA:
        return JiebaAnalyzer()
    return StandardAnalyzer()

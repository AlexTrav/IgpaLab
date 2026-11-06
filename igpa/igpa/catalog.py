"""Справочники формы АСУ «ТУРАН»: типы мероприятий и статусы (уровни).

Порядок типов совпадает с колонками J–Y «Сводной выгрузки студентов по IGPA»,
asu_title – текст шапки колонки без « (баллы)» символ в символ (сверяется тестом с шаблоном).
Справочник АСУ (2026/27) шире Положения 2025 года: четыре типа в Положении отсутствуют.
"""

import re
from dataclasses import dataclass
from enum import Enum


class Profile(str, Enum):
    IROS = "IROS"
    SSCI = "SSCI"


class Block(str, Enum):
    RESEARCH = "research"    # карта iROS, Приложение 1
    ONE_TIME = "one_time"    # SSCI, разовые мероприятия
    PERMANENT = "permanent"  # SSCI, постоянные университетские проекты в течение года

    @property
    def profile(self) -> Profile:
        return Profile.IROS if self is Block.RESEARCH else Profile.SSCI


@dataclass(frozen=True)
class Category:
    code: str
    column: str
    block: Block
    name: str
    asu_title: str
    in_regulation: bool

    @property
    def profile(self) -> Profile:
        return self.block.profile

    @property
    def export_header(self) -> str:
        return f"{self.asu_title} (баллы)"


@dataclass(frozen=True)
class Status:
    code: str
    family: Block
    asu_name: str


_R, _O, _P = Block.RESEARCH, Block.ONE_TIME, Block.PERMANENT

CATEGORIES: tuple[Category, ...] = (
    Category("IROS_EVENT", "J", _R, "Участие или организация научных мероприятий",
             "Участие или организация научных мероприятий(Вид: конференций, семинаров/вебинаров, конкурсов "
             "научных проектов, олимпиад, хакатонов, научных выставок и др.)", True),
    Category("IROS_TALK", "K", _R, "Выступление с докладом",
             "Выступление с докладом(научно-исследовательская работа студента под руководством преподавателя) "
             "на научно практической конференции, или в других научных мероприятиях", False),
    Category("IROS_PUBLICATION", "L", _R, "Публикации и результаты",
             "Публикации и результаты(доклад, презентация, статья, заявка или охранное свидетельство объекты "
             "интеллектуальной собственности и авторского права, сертификат о владении навыками работы на научном "
             "оборудовании)", True),
    Category("IROS_PROJECT", "M", _R, "Участие в научных проектах и стартапах",
             "Участие в действующих научно-исследовательских проектах и программах, коммерциализации, стартапах, "
             "резидент бизнес инкубатора", True),
    Category("IROS_INTERNSHIP", "N", _R, "Научная стажировка",
             "Научная стажировка для магистрантов и докторантов", False),
    Category("IROS_PRIZE", "O", _R, "Призовое место в научных конкурсах",
             "Призовое место в конкурсе научно-исследовательских работ студентов, хакатонах, предметных олимпиадах",
             True),
    Category("SSCI_VOLUNTEER", "P", _O, "Участие в волонтёрском движении",
             "Участие в волонтерском движении", True),
    # в АСУ текст шапки обрезан на «и », отсюда пробел в конце
    Category("SSCI_INTELLECTUAL", "Q", _O, "Участие в интеллектуальных и дебатных мероприятиях",
             "Участие в интеллектуальных, дебатных мероприятиях. Мероприятиях по развитию soft skills(мастер-классы, "
             "карьерные ярмарки и ", True),
    Category("SSCI_INTELLECTUAL_PRIZE", "R", _O, "Достижения в интеллектуальных и дебатных мероприятиях",
             "Достижения в интеллектуальных, дебатных мероприятиях.", True),
    Category("SSCI_SPORT", "S", _O, "Достижения в спорте",
             "Достижения в спорте (призовое место (Виды спорта включенные в программу Универсиады) в личном и / или "
             "командном зачете)", True),
    Category("SSCI_SOCIAL_PROJECT", "T", _O, "Организация творческих и социальных проектов",
             "Организация творческих, социальных, экологических, благотворительных проектов", True),
    Category("SSCI_IMAGE_PROJECT", "U", _P, "Участие в имиджевых проектах",
             "Участие в имиджевых проектах: Мистер и Мисс «Туран», Посвящение в студенты, Вручение дипломов, "
             "Этнофестиваль и др.", True),
    Category("SSCI_STUDENT_ORG", "V", _P, "Членство в студенческих организациях, староста",
             "Членство в студенческих организациях, старосты академических групп.", True),
    Category("SSCI_LEADERSHIP", "W", _P, "Руководство студенческими организациями",
             "Руководство в студенческих организациях и создание новых студенческих инициатив.", False),
    Category("SSCI_UNIVERSITY_IMAGE", "X", _P, "Вклад в имидж университета",
             "Вклад в имидж университета (публикации, интервью, введение полезных аккаунтов).", True),
    Category("SSCI_UNIT_VOLUNTEER", "Y", _P, "Волонтёрство в структурных подразделениях",
             "Волонтерство в Структурных подразделениях (ДМиПК, КДМ, ЦКиЛ и др.).", False),
)

# один список на оба профиля: студент может выбрать статус «чужой» карты
STATUSES: tuple[Status, ...] = (
    Status("IROS_OVPO", _R, "ОВПО"),
    Status("IROS_REP_CITY", _R, "Республиканский, Городской"),
    Status("IROS_INT_RK", _R, "Международный в Республике Казахстан"),
    Status("IROS_INT_ABROAD", _R, "Международный, за рубежом"),
    Status("SSCI_UNIVERSITY", _O, "Университетские"),
    Status("SSCI_CITY_REGION", _O, "Городской, региональный"),
    Status("SSCI_REPUBLIC", _O, "Республиканский"),
    Status("SSCI_INTERNATIONAL", _O, "Международные"),
    Status("SSCI_PERMANENT", _P, "В рамках постоянно реализуемых университетских проектов (в течение года)"),
)

CATEGORY_BY_CODE = {c.code: c for c in CATEGORIES}
STATUS_BY_CODE = {s.code: s for s in STATUSES}


def categories(profile: Profile | None = None, block: Block | None = None) -> tuple[Category, ...]:
    return tuple(c for c in CATEGORIES
                 if (profile is None or c.profile is profile) and (block is None or c.block is block))


def statuses(family: Block) -> tuple[Status, ...]:
    return tuple(s for s in STATUSES if s.family is family)


def _norm(text: str) -> str:
    text = text.casefold().replace("ё", "е").replace("«", '"').replace("»", '"')
    text = re.sub(r"\(баллы\)\s*$", "", text)
    return re.sub(r"\s+", " ", text).strip()


_CATEGORY_TEXT = {_norm(t): c for c in CATEGORIES for t in (c.code, c.name, c.asu_title)}
_STATUS_TEXT = {_norm(t): s for s in STATUSES for t in (s.code, s.asu_name)}


def find_category(text: str) -> Category | None:
    """Тип по коду, короткому названию или тексту АСУ (регистр, «ё», пробелы и « (баллы)» не важны)."""
    return _CATEGORY_TEXT.get(_norm(text))


def find_status(text: str) -> Status | None:
    return _STATUS_TEXT.get(_norm(text))

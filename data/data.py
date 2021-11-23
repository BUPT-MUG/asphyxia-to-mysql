from typing_extensions import Final


class SDVXDBMusicData:

    GAME = "sdvx"
    VERSION = 6

    CLEAR_TYPE_NO_PLAY: Final[int] = 50
    CLEAR_TYPE_FAILED: Final[int] = 100
    CLEAR_TYPE_CLEAR: Final[int] = 200
    CLEAR_TYPE_HARD_CLEAR: Final[int] = 300
    CLEAR_TYPE_ULTIMATE_CHAIN: Final[int] = 400
    CLEAR_TYPE_PERFECT_ULTIMATE_CHAIN: Final[int] = 500
    GRADE_NO_PLAY: Final[int] = 100
    GRADE_D: Final[int] = 200
    GRADE_C: Final[int] = 300
    GRADE_B: Final[int] = 400
    GRADE_A: Final[int] = 500
    GRADE_A_PLUS: Final[int] = 550
    GRADE_AA: Final[int] = 600
    GRADE_AA_PLUS: Final[int] = 650
    GRADE_AAA: Final[int] = 700
    GRADE_AAA_PLUS: Final[int] = 800
    GRADE_S: Final[int] = 900

    GAME_CLEAR_TYPE_NO_PLAY: Final[int] = 0
    GAME_CLEAR_TYPE_FAILED: Final[int] = 1
    GAME_CLEAR_TYPE_CLEAR: Final[int] = 2
    GAME_CLEAR_TYPE_HARD_CLEAR: Final[int] = 3
    GAME_CLEAR_TYPE_ULTIMATE_CHAIN: Final[int] = 4
    GAME_CLEAR_TYPE_PERFECT_ULTIMATE_CHAIN: Final[int] = 5

    GAME_GRADE_NO_PLAY: Final[int] = 0
    GAME_GRADE_D: Final[int] = 1
    GAME_GRADE_C: Final[int] = 2
    GAME_GRADE_B: Final[int] = 3
    GAME_GRADE_A: Final[int] = 4
    GAME_GRADE_A_PLUS: Final[int] = 5
    GAME_GRADE_AA: Final[int] = 6
    GAME_GRADE_AA_PLUS: Final[int] = 7
    GAME_GRADE_AAA: Final[int] = 8
    GAME_GRADE_AAA_PLUS: Final[int] = 9
    GAME_GRADE_S: Final[int] = 10

    def __game_to_db_clear_type(self, clear_type: int) -> int:
        return {
            self.GAME_CLEAR_TYPE_NO_PLAY: self.CLEAR_TYPE_NO_PLAY,
            self.GAME_CLEAR_TYPE_FAILED: self.CLEAR_TYPE_FAILED,
            self.GAME_CLEAR_TYPE_CLEAR: self.CLEAR_TYPE_CLEAR,
            self.GAME_CLEAR_TYPE_HARD_CLEAR: self.CLEAR_TYPE_HARD_CLEAR,
            self.GAME_CLEAR_TYPE_ULTIMATE_CHAIN: self.CLEAR_TYPE_ULTIMATE_CHAIN,
            self.GAME_CLEAR_TYPE_PERFECT_ULTIMATE_CHAIN: self.CLEAR_TYPE_PERFECT_ULTIMATE_CHAIN,
        }[clear_type]

    def __game_to_db_grade(self, grade: int) -> int:
        return {
            self.GAME_GRADE_NO_PLAY: self.GRADE_NO_PLAY,
            self.GAME_GRADE_D: self.GRADE_D,
            self.GAME_GRADE_C: self.GRADE_C,
            self.GAME_GRADE_B: self.GRADE_B,
            self.GAME_GRADE_A: self.GRADE_A,
            self.GAME_GRADE_A_PLUS: self.GRADE_A_PLUS,
            self.GAME_GRADE_AA: self.GRADE_AA,
            self.GAME_GRADE_AA_PLUS: self.GRADE_AA_PLUS,
            self.GAME_GRADE_AAA: self.GRADE_AAA,
            self.GAME_GRADE_AAA_PLUS: self.GRADE_AAA_PLUS,
            self.GAME_GRADE_S: self.GRADE_S,
        }[grade]

    def __init__(self, songid=0, chart=0, points=0, clear_type=0, grade=0, stats={}, timestamp=0, update=0):
        self.songid = songid
        self.chart = chart
        self.points = points
        self.clear_type = clear_type
        self.grade = grade
        self.timestamp = timestamp
        self.update = update
        self.stats = stats

    def from_asyphxia_data(self, data: dict):
        self.songid = data['mid']
        self.chart = data['type']
        self.points = data['score']
        self.clear_type = self.__game_to_db_clear_type(data['clear'])
        self.grade = self.__game_to_db_grade(data['grade'])
        self.stats = {
            'btn_rate': data['buttonRate'],
            'long_rate': data['longRate'],
            'vol_rate': data['volRate'],
            'critical': 0,
            'near': 0,
            'error': 0,
        }
        # ms to s
        self.timestamp = data['createdAt']['$$date'] // 1000
        self.update = data['updatedAt']['$$date'] // 1000

    def __str__(self) -> str:
        return '{}'.format(self.__dict__)

import json
from typing import Any, List
import sqlalchemy

from data.data import SDVXDBMusicData


class _BytesEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, bytes):
            # We're abusing lists here, we have a mixed type
            return ['__bytes__'] + [b for b in obj]  # type: ignore
        return json.JSONEncoder.default(self, obj)


def deserialize(data: str) -> dict:
    """
    Given a string, deserialize it from JSON.
    """
    if data is None:
        return {}

    def fix(jd: Any) -> Any:
        if type(jd) == dict:
            # Fix each element in the dictionary.
            for key in jd:
                jd[key] = fix(jd[key])
            return jd

        if type(jd) == list:
            # Could be serialized by us, could be a normal list.
            if len(jd) >= 1 and jd[0] == '__bytes__':
                # This is a serialized bytestring
                return bytes(jd[1:])

            # Possibly one of these is a dictionary/list/serialized.
            for i in range(len(jd)):
                jd[i] = fix(jd[i])
            return jd

        # Normal value, its deserialized version is itself.
        return jd

    return fix(json.loads(data))


class Engine:
    def __init__(self, config: dict):
        def sqlalchemy_url(config: dict) -> str:
            return f"mysql://{config['mysql']['user']}:{config['mysql']['password']}@{config['mysql']['address']}/{config['mysql']['database']}?charset=utf8mb4"
        self.engine = sqlalchemy.create_engine(
            sqlalchemy_url(config),
            pool_recycle=3600,
        )

    def __get_machine_id(self, pcbid: str) -> int:
        sql = f"SELECT id FROM machine WHERE pcbid = :pcbid"
        cursor = self.engine.execute(sqlalchemy.text(sql), {'pcbid': pcbid})
        if cursor.rowcount == 0:
            return -1
        return cursor.fetchone()['id']

    def __get_user_id(self, card: str) -> int:
        sql = f"SELECT userid FROM card WHERE id = :card"
        cursor = self.engine.execute(sqlalchemy.text(sql), {'card': card})
        if cursor.rowcount == 0:
            return -1
        return cursor.fetchone()['userid']

    def __get_old_score(self, userid: int, game: str, version: int, songid: int, songchart: int):
        sql = (
            "SELECT music.songid AS songid, music.chart AS chart, score.timestamp AS timestamp, score.update AS `update`, score.lid AS lid, " +
            "(select COUNT(score_history.timestamp) FROM score_history WHERE score_history.musicid = music.id AND score_history.userid = :userid) AS plays, " +
            "score.points AS points, score.data AS data FROM score, music WHERE score.userid = :userid AND score.musicid = music.id " +
            "AND music.game = :game AND music.version = :version AND music.songid = :songid AND music.chart = :songchart"
        )
        cursor = self.engine.execute(
            sqlalchemy.text(sql),
            {
                'userid': userid,
                'game': game,
                'version': version,
                'songid': songid,
                'songchart': songchart,
            },
        )
        if cursor.rowcount != 1:
            # score doesn't exist
            return None

        result = cursor.fetchone()
        return SDVXDBMusicData(
            songid=result['songid'],
            chart=result['chart'],
            points=result['points'],
            timestamp=result['timestamp'],
            update=result['update'],
            stats=deserialize(result['data']),
        )

    def __get_musicid(self, game: str, version: int, songid: int, songchart: int) -> int:
        """
        Given a game/version/songid/chart, look up the unique music ID for this song.

        Parameters:
            game - Enum value representing a game series.
            version - Integer representing which version of the game.
            songid - ID of the song according to the game.
            songchart - Chart number according to the game.

        Returns:
            Integer representing music ID if found or raises an exception otherwise.
        """
        sql = (
            "SELECT id FROM music WHERE songid = :songid AND chart = :chart AND game = :game AND version = :version"
        )
        cursor = self.engine.execute(
            sqlalchemy.text(sql), {'songid': songid, 'chart': songchart, 'game': game, 'version': version})
        if cursor.rowcount != 1:
            # music doesn't exist
            return -1
        result = cursor.fetchone()
        return result['id']

    def __put_score(
        self,
        game: str,
        version: int,
        userid: int,
        songid: int,
        songchart: int,
        location: int,
        points: int,
        data: dict,
        new_record: bool,
        timestamp: int,
        update: int,
    ):
        musicid = self.__get_musicid(game, version, songid, songchart)
        if musicid == -1:
            return

        # Add to user score
        if new_record:
            # We want to update the timestamp/location to now if its a new record.
            sql = (
                "INSERT INTO `score` (`userid`, `musicid`, `points`, `data`, `timestamp`, `update`, `lid`) " +
                "VALUES (:userid, :musicid, :points, :data, :timestamp, :update, :location) " +
                "ON DUPLICATE KEY UPDATE data = VALUES(data), points = VALUES(points), " +
                "timestamp = VALUES(timestamp), `update` = VALUES(`update`), lid = VALUES(lid)"
            )
        else:
            # We only want to add the timestamp if it is new.
            sql = (
                "INSERT INTO `score` (`userid`, `musicid`, `points`, `data`, `timestamp`, `update`, `lid`) " +
                "VALUES (:userid, :musicid, :points, :data, :timestamp, :update, :location) " +
                "ON DUPLICATE KEY UPDATE data = VALUES(data), points = VALUES(points), `update` = VALUES(`update`)"
            )
        self.engine.execute(
            sqlalchemy.text(sql),
            {
                'userid': userid,
                'musicid': musicid,
                'points': points,
                'data': json.dumps(data, cls=_BytesEncoder),
                'timestamp': timestamp,
                'update': update,
                'location': location,
            }
        )

    def __put_history_score(
        self,
        game: str,
        version: int,
        userid: int,
        songid: int,
        songchart: int,
        location: int,
        points: int,
        data: dict,
        new_record: bool,
        timestamp: int,
    ):
        # First look up the song/chart from the music DB
        musicid = self.__get_musicid(game, version, songid, songchart)
        if musicid == -1:
            return

        # Add to score history
        sql = (
            "INSERT INTO `score_history` (userid, musicid, timestamp, lid, new_record, points, data) " +
            "VALUES (:userid, :musicid, :timestamp, :location, :new_record, :points, :data)"
        )
        try:
            self.engine.execute(
                sqlalchemy.text(sql),
                {
                    'userid': userid if userid is not None else 0,
                    'musicid': musicid,
                    'timestamp': timestamp,
                    'location': location,
                    'new_record': 1 if new_record else 0,
                    'points': points,
                    'data': json.dumps(data, cls=_BytesEncoder),
                },
            )
        except Exception:
            return

    def __update_score(self, userid: int, lid: int, data: SDVXDBMusicData):
        # Range check clear type
        if data.clear_type not in [
            SDVXDBMusicData.CLEAR_TYPE_NO_PLAY,
            SDVXDBMusicData.CLEAR_TYPE_FAILED,
            SDVXDBMusicData.CLEAR_TYPE_CLEAR,
            SDVXDBMusicData.CLEAR_TYPE_HARD_CLEAR,
            SDVXDBMusicData.CLEAR_TYPE_ULTIMATE_CHAIN,
            SDVXDBMusicData.CLEAR_TYPE_PERFECT_ULTIMATE_CHAIN,
        ]:
            return

        #  Range check grade
        if data.grade not in [
            SDVXDBMusicData.GRADE_NO_PLAY,
            SDVXDBMusicData.GRADE_D,
            SDVXDBMusicData.GRADE_C,
            SDVXDBMusicData.GRADE_B,
            SDVXDBMusicData.GRADE_A,
            SDVXDBMusicData.GRADE_A_PLUS,
            SDVXDBMusicData.GRADE_AA,
            SDVXDBMusicData.GRADE_AA_PLUS,
            SDVXDBMusicData.GRADE_AAA,
            SDVXDBMusicData.GRADE_AAA_PLUS,
            SDVXDBMusicData.GRADE_S,
        ]:
            return
        # Score history is verbatum, instead of highest score
        history = {
            "combo": 0,
            "grade": 0,
            "stats": {
                "near": 0,
                "error": 0,
                "btn_rate": 0,
                "critical": 0,
                "vol_rate": 0,
                "long_rate": 0
            },
            "clear_type": 0
        }
        oldpoints = data.points
        oldscore = self.__get_old_score(
            userid, data.GAME, data.VERSION, data.songid, data.chart)
        timestamp = data.timestamp
        update = data.update
        if oldscore is None:
            # If it is a new score, create a new dictionary to add to
            scoredata = {
                "combo": 0,
                "grade": 0,
                "stats": {
                    "near": 0,
                    "error": 0,
                    "btn_rate": 0,
                    "critical": 0,
                    "vol_rate": 0,
                    "long_rate": 0
                },
                "clear_type": 0
            }
            raised = True
            highscore = True
        else:
            # Set the score to any new record achieved
            raised = data.points > oldscore.points
            highscore = data.points >= oldscore.points
            data.points = max(oldscore.points, data.points)
            scoredata = oldscore.stats
            timestamp = min(oldscore.timestamp, data.timestamp)
            update = max(oldscore.update, data.update)

        # Replace clear type and grade
        scoredata['clear_type'] = max(scoredata['clear_type'], data.clear_type)
        history['clear_type'] = data.clear_type
        scoredata['grade'] = max(scoredata['grade'], data.grade)
        history['grade'] = data.grade

        # If we have play stats, replace it
        if data.stats is not None:
            if raised:
                # We have stats, and there's a new high score, update the stats
                scoredata['stats'] = data.stats
            history['stats'] = data.stats

        # Write the new score back
        self.__put_score(
            data.GAME,
            data.VERSION,
            userid,
            data.songid,
            data.chart,
            lid,
            data.points,
            scoredata,
            highscore,
            timestamp,
            update,
        )

        # Save the history of this score too
        self.__put_history_score(
            data.GAME,
            data.VERSION,
            userid,
            data.songid,
            data.chart,
            lid,
            oldpoints,
            history,
            raised,
            data.timestamp
        )

    def sync_to_mysql(self, pcbid: str, card: str, datas: List[SDVXDBMusicData]):
        print(f"Begin to sync data [pcbid: {pcbid}, card: {card}] to MySQL")
        lid = self.__get_machine_id(pcbid)
        if lid == -1:
            print("No machine corresponding to the pcbid")
            return
        uid = self.__get_user_id(card)
        if uid == -1:
            print("No user corresponding to the card")
            return
        for d in datas:
            self.__update_score(uid, lid, d)
            print(f"sync data: {d} to MySQL success")

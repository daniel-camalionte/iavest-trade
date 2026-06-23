import json

from model.Mt5Log import Mt5LogModel

class Mt5LogRule():

    def __init__(self):
        pass

    def insert(self, data):
        win = data.get("win") or {}
        win_candle = win.get("candle") or {}
        wdo = data.get("wdo") or {}
        wdo_candle = wdo.get("candle") or {}

        modMt5Log = Mt5LogModel()
        id_mt5_log = modMt5Log.save({
            "account_number":       data.get("account_number"),
            "id_estrategia":        data.get("id_estrategia"),
            "versao":               data.get("versao"),
            "password":             data.get("password"),
            "periodo_timeframe":    data.get("periodo_timeframe"),
            "ativos_sincronizados": 1 if data.get("ativos_sincronizados") else 0,

            "win_ativo_atual":      win.get("ativo_atual"),
            "win_offset":           win.get("offset"),
            "win_lastbar_date":     win.get("lastbar_date"),
            "win_id_symbols":       win_candle.get("id_symbols"),
            "win_datetime":         win_candle.get("datetime"),
            "win_open":             win_candle.get("open"),
            "win_high":             win_candle.get("high"),
            "win_low":              win_candle.get("low"),
            "win_close":            win_candle.get("close"),
            "win_tick_vol":         win_candle.get("tick_vol"),
            "win_vol":              win_candle.get("vol"),
            "win_spread":           win_candle.get("spread"),

            "wdo_ativo_atual":      wdo.get("ativo_atual"),
            "wdo_offset":           wdo.get("offset"),
            "wdo_lastbar_date":     wdo.get("lastbar_date"),
            "wdo_id_symbols":       wdo_candle.get("id_symbols"),
            "wdo_datetime":         wdo_candle.get("datetime"),
            "wdo_open":             wdo_candle.get("open"),
            "wdo_high":             wdo_candle.get("high"),
            "wdo_low":              wdo_candle.get("low"),
            "wdo_close":            wdo_candle.get("close"),
            "wdo_tick_vol":         wdo_candle.get("tick_vol"),
            "wdo_vol":              wdo_candle.get("vol"),
            "wdo_spread":           wdo_candle.get("spread"),

            "payload": json.dumps(data, ensure_ascii=False)
        })

        if not id_mt5_log:
            return {'msg': 'Erro ao registrar log'}, 500

        return {'id_mt5_log': id_mt5_log}, 200

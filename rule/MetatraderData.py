from model.Mt5Candles import Mt5CandlesModel

HARDCODED_PASSWORD = "1IepXepao3"

class MetatraderDataRule():

    def __init__(self):
        pass

    def insert_candles(self, data):
        if data.get("password") != HARDCODED_PASSWORD:
            return {'msg': 'Senha incorreta'}, 401

        candles_input = []
        for key in ("candle_win", "candle_wdo"):
            candle = data.get(key)
            if not candle:
                continue
            # normaliza id_symbol -> id_symbols (candle_wdo envia singular)
            if "id_symbol" in candle and "id_symbols" not in candle:
                candle["id_symbols"] = candle["id_symbol"]
            candles_input.append(candle)

        if not candles_input:
            return {'msg': 'Nenhum candle enviado'}, 400

        model_fields = Mt5CandlesModel().fields()
        inserted = []
        skipped = []

        for candle in candles_input:
            id_symbols   = candle.get("id_symbols")
            datetime_val = candle.get("datetime")

            if not id_symbols or not datetime_val:
                continue

            existing = (
                Mt5CandlesModel()
                .where(['id_symbols', '=', id_symbols])
                .where(['datetime',   '=', datetime_val])
                .limit(1)
                .find()
            )

            if existing:
                skipped.append({"id_symbols": id_symbols, "datetime": datetime_val})
                continue

            row    = {k: candle[k] for k in candle if k in model_fields}
            new_id = Mt5CandlesModel().save(row)

            if not new_id:
                return {'msg': 'Erro ao inserir candle'}, 500

            inserted.append({"id_mt5_candle": new_id, "id_symbols": id_symbols, "datetime": datetime_val})

        return {'inserted': inserted, 'skipped': skipped}, 200

from library.base.BaseModel import BaseModel

class Mt5LogModel(BaseModel):

    def __init__(self):
        super().__init__()
        pass

    def table(self):
        return 'mt5_log'

    def pk(self):
        return 'id_mt5_log'

    def fields(self):
        fields = {
                    "id_mt5_log": 'id_mt5_log',
                    "account_number": 'account_number',
                    "id_estrategia": 'id_estrategia',
                    "versao": 'versao',
                    "password": 'password',
                    "periodo_timeframe": 'periodo_timeframe',
                    "ativos_sincronizados": 'ativos_sincronizados',

                    "win_ativo_atual": 'win_ativo_atual',
                    "win_offset": 'win_offset',
                    "win_lastbar_date": 'win_lastbar_date',
                    "win_id_symbols": 'win_id_symbols',
                    "win_datetime": 'win_datetime',
                    "win_open": 'win_open',
                    "win_high": 'win_high',
                    "win_low": 'win_low',
                    "win_close": 'win_close',
                    "win_tick_vol": 'win_tick_vol',
                    "win_vol": 'win_vol',
                    "win_spread": 'win_spread',

                    "wdo_ativo_atual": 'wdo_ativo_atual',
                    "wdo_offset": 'wdo_offset',
                    "wdo_lastbar_date": 'wdo_lastbar_date',
                    "wdo_id_symbols": 'wdo_id_symbols',
                    "wdo_datetime": 'wdo_datetime',
                    "wdo_open": 'wdo_open',
                    "wdo_high": 'wdo_high',
                    "wdo_low": 'wdo_low',
                    "wdo_close": 'wdo_close',
                    "wdo_tick_vol": 'wdo_tick_vol',
                    "wdo_vol": 'wdo_vol',
                    "wdo_spread": 'wdo_spread',

                    "payload": 'payload',
                    "created_at": 'created_at'
                }

        return fields

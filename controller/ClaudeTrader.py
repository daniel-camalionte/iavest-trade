import json

from flask import request
from flask.views import MethodView

from rule.ClaudeTraderOrdem import ClaudeTraderOrdemRule
from model.ControllerError import ControllerError


class ClaudeTraderOrdemController(MethodView):
    """POST /claude-trader/ordem

    Chamado pelo EA (MT5) com senha própria. Entrega a ordem de execução
    reconciliada com a posição real que o EA reporta ter aberto. Atende
    QUALQUER estratégia que a conta assine (multi-estratégia, filtrado por
    id_estrategia). Só LEITURA da guia (claude_trader_operacao), gerada pelo
    cérebro no iavest-backend.
    """

    def post(self):
        data = None
        try:
          # Tenta pegar do form data (formato: payload={json})
          if request.form and 'payload' in request.form:
              payload_str = request.form.get('payload')
              data = json.loads(payload_str)

          # Tenta pegar do body raw (formato: payload={json})
          if not data and request.data:
              raw_data = request.data.decode('utf-8')
              if raw_data.startswith('payload='):
                  payload_str = raw_data[8:]  # Remove "payload="
                  data = json.loads(payload_str)
              else:
                  # Tenta como JSON puro
                  data = json.loads(raw_data)

          # Tenta como JSON direto
          if not data:
              data = request.get_json(force=True, silent=True)
              if isinstance(data, str):
                  data = json.loads(data)

          return ClaudeTraderOrdemRule.entregar(data or {})

        except json.JSONDecodeError as e:
            return {"msg": "JSON inválido: " + str(e)}, 422
        except Exception as e:
            msg = ControllerError().default(e)
            return msg, 500

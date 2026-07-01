"""
Entrega de ordens do Claude Trader pro MT5 (EA chama via POST, com senha própria).

Só LEITURA da claude_trader_operacao — quem decide abrir/manter/mover_stop/encerrar
é o cérebro no iavest-backend (rule/ClaudeTrader.py), chamado pelo schedule a cada
~1min. Este app (iavest-trade) é o consumer: traduz o estado atual da guia pra
instrução de execução, reconciliando com a posição REAL que o EA reporta ter aberto.

V2.6 — DOIS TRILHOS por estratégia (atende 1 ou N estratégias, filtrado por id_estrategia):
  - PRINCIPAL  (origem='principal') — a guia normal. Quem está dentro segue ela.
  - REENTRADA  (origem='reentrada') — op paralela aberta pelo cérebro num sinal forte
    fresco enquanto a principal está aberta. Serve quem está FLAT (saiu na mão, estopou
    ou logou atrasado). Quem está dentro da principal NUNCA vê a reentrada.

Reconciliação:
  - guia inexistente hoje + EA com posição           -> encerrar (posição órfã)
  - principal aberta + EA com posição (mesma dir)     -> propaga stop da op que ele segue
  - posição na direção errada                         -> encerrar (sai da errada)
  - op que ele segue encerrou + EA ainda posicionado  -> encerrar
  - EA FLAT com entrega ativa (saiu)                  -> grava 'encerrar_flat' (saída manual)
  - EA FLAT e elegível                                -> 'abrir' op FRESCA não-operada
                                                         (reentrada tem prioridade; principal só
                                                          dentro da janela de entrada — login
                                                          atrasado NÃO persegue posição em curso)
  - nada mudou                                        -> [] (não grava nada)

Trava anti-perseguição: por id_operacao. Uma op da qual o cliente já saiu não é
reoferecida; mas uma op NOVA (reentrada) é uma entrega nova, então não cai na trava.
"""
from datetime import datetime, timezone, timedelta

import config.env as memory
from model.ClaudeTrader import ClaudeTraderModel
from model.ClaudeTraderMt5Ordens import ClaudeTraderMt5OrdensModel
from model.Generico import GenericoModel

ID_ESTRATEGIA_CLAUDE_TRADER = 6   # referência; a rota NÃO bloqueia mais por id (libera p/ ids assinados)
ID_ATIVOS_BASE = 1
BRASILIA = timezone(timedelta(hours=-3))

# Login atrasado NÃO persegue posição em andamento: só entra numa op aberta há no máximo este
# tempo (a entrada normal é capturada em 1-2 polls; depois disso a op é "em curso" → espera a
# próxima fresca/reentrada). Tunável — afeta também a 1ª entrada da principal.
JANELA_ENTRADA_MIN = 5


class ClaudeTraderOrdemRule:

    @staticmethod
    def entregar(data):
        if str(data.get("password")) != str(memory.claude_trader_mt5["PASSWORD"]):
            return {"msg": "Senha incorreta"}, 401

        try:
            id_estrategia = int(data.get("id_estrategia"))
        except (TypeError, ValueError):
            return {"msg": "'id_estrategia' é obrigatório"}, 400

        account_number = data.get("account_number")
        if not account_number:
            return {"msg": "'account_number' é obrigatório"}, 400

        tem_posicao_aberta = bool(data.get("tem_posicao_aberta"))
        tipo_posicao_mt5 = data.get("tipo_posicao_mt5")

        if tem_posicao_aberta and tipo_posicao_mt5 not in ("buy", "sell"):
            return {"msg": "'tipo_posicao_mt5' deve ser 'buy' ou 'sell' quando 'tem_posicao_aberta' é true"}, 400

        # A rota libera qualquer estratégia que a CONTA assine (multi-estratégia). A assinatura
        # por id_estrategia é a barreira de acesso — não mais um id fixo.
        if not ClaudeTraderOrdemRule._conta_assina_estrategia(account_number, id_estrategia):
            return {"msg": "Conta não encontrada, inativa ou sem assinatura da estratégia"}, 401

        principal = ClaudeTraderOrdemRule._guia_hoje(id_estrategia)

        acao, tipo_posicao, motivo, op_alvo = ClaudeTraderOrdemRule._reconciliar(
            principal, tem_posicao_aberta, tipo_posicao_mt5, account_number, id_estrategia)

        if not acao:
            return [], 200

        op = op_alvo or {}
        status = "encerrada" if acao in ("encerrar", "encerrar_flat") else "aberta"

        ClaudeTraderMt5OrdensModel().save({
            "id_operacao":                 op.get("id_operacao"),
            "account_number":              account_number,
            "id_estrategia":               id_estrategia,
            "status":                      status,
            "tipo_posicao":                tipo_posicao,
            "acao":                        acao,
            "preco_entrada":               op.get("preco_entrada"),
            "stop_loss":                   op.get("stop_loss"),
            "stop_gain":                   op.get("stop_gain"),
            "posicao_atual_recebida":      data.get("posicao_atual"),
            "tem_posicao_aberta_recebida": 1 if tem_posicao_aberta else 0,
            "tipo_posicao_mt5_recebida":   tipo_posicao_mt5,
            "motivo":                      motivo,
        })

        # 'encerrar_flat' é só REGISTRO da saída manual — o EA já está flat, não comanda nada.
        if acao == "encerrar_flat":
            return [], 200

        return [{
            "id_operacao":   op.get("id_operacao"),
            "tipo_posicao":  tipo_posicao,
            "acao":          acao,
            "preco_entrada": op.get("preco_entrada"),
            "stop_loss":     op.get("stop_loss"),
            "stop_gain":     op.get("stop_gain"),
            "motivo":        motivo,
        }], 200

    # ------------------------------------------------------------------ reconciliação
    @staticmethod
    def _reconciliar(principal, tem_posicao_aberta, tipo_posicao_mt5, account_number, id_estrategia):
        """Retorna (acao, tipo_posicao, motivo, op_alvo) ou (None, None, None, None).
        op_alvo = a op cujos dados (preço/stop/gain/id) vão na entrega/resposta."""

        # ---------- sem PRINCIPAL hoje ----------
        if not principal:
            if tem_posicao_aberta:
                ultima = ClaudeTraderOrdemRule._ultima_geral(account_number, id_estrategia)
                if ultima and ultima["id_operacao"] is None and ultima["acao"] == "encerrar":
                    return (None, None, None, None)
                return ("encerrar", tipo_posicao_mt5,
                        "Reconciliação: EA reportou posição aberta sem operação ativa hoje — encerra por segurança",
                        None)
            return (None, None, None, None)

        # ---------- EA COM POSIÇÃO ----------
        if tem_posicao_aberta:
            op_seg = ClaudeTraderOrdemRule._op_que_segue(account_number, id_estrategia, principal)

            if op_seg and op_seg["status"] == "aberta":
                if tipo_posicao_mt5 != op_seg["tipo_posicao"]:
                    ultima = ClaudeTraderOrdemRule._ultima_entrega(account_number, id_estrategia, op_seg["id_operacao"])
                    if ultima and ultima["acao"] == "encerrar":
                        return (None, None, None, None)
                    return ("encerrar", tipo_posicao_mt5,
                            "Reconciliação: EA tem posição %s mas a op é %s — encerra a posição errada"
                            % (tipo_posicao_mt5, op_seg["tipo_posicao"]), op_seg)
                # mesma direção → propaga o stop da op que ele segue, se mudou (proteção por alvo)
                ultima = ClaudeTraderOrdemRule._ultima_entrega(account_number, id_estrategia, op_seg["id_operacao"])
                if not ultima or ultima.get("stop_loss") != op_seg["stop_loss"]:
                    return ("mover_stop", op_seg["tipo_posicao"], op_seg.get("motivo"), op_seg)
                # CONFIRMACAO DE ABERTURA: 1a vez que vemos o EA segurando esta op (tem_posicao=1),
                # grava um marcador (linha com tem_posicao_aberta_recebida=1). E o que distingue
                # "abriu de verdade" de "ainda nao abriu (lag)" quando ele ficar flat depois — sem
                # isso, um flat logo apos o 'abrir' era lido como saida manual (bug do lag).
                if not ClaudeTraderOrdemRule._confirmada(account_number, id_estrategia, op_seg["id_operacao"]):
                    return ("manter", op_seg["tipo_posicao"], "Abertura confirmada pelo EA", op_seg)
                return (None, None, None, None)

            # a op que ele seguia encerrou (ou não achou) e ele ainda tem posição → encerra
            ref = op_seg or principal
            ultima = ClaudeTraderOrdemRule._ultima_entrega(account_number, id_estrategia, ref["id_operacao"])
            if ultima and ultima["acao"] == "encerrar":
                return (None, None, None, None)
            return ("encerrar", tipo_posicao_mt5 or ref.get("tipo_posicao"),
                    ref.get("motivo") or "Reconciliação: op encerrada e EA ainda posicionado — encerra",
                    ref)

        # ---------- EA FLAT ----------
        return ClaudeTraderOrdemRule._resolver_flat(principal, account_number, id_estrategia)

    @staticmethod
    def _resolver_flat(principal, account_number, id_estrategia):
        """Cliente FLAT. (1) Se ele acabou de sair de uma op (entrega viva = abrir/mover_stop),
        registra a SAÍDA FLAT 1x. (2) Senão, oferece a op FRESCA que ele não operou — reentrada
        tem prioridade; principal só dentro da janela de entrada (login atrasado não persegue)."""

        # 1) acabou de sair? última entrega geral ainda "viva" mas o EA está flat.
        ultima = ClaudeTraderOrdemRule._ultima_geral(account_number, id_estrategia)
        if ultima and ultima["acao"] in ("abrir", "mover_stop", "manter"):
            # SO e saida real se a abertura foi CONFIRMADA (o EA reportou tem_posicao=1 nesta op em
            # algum poll). Senao, "flat + abrir entregue" = ainda NAO abriu (lag entre entregar o
            # 'abrir' e o EA executar/confirmar) -> ESPERA, nao mata a ordem. Antes isso virava
            # encerrar_flat indevido e abandonava a entrada em segundos (bug do lag).
            if ClaudeTraderOrdemRule._confirmada(account_number, id_estrategia, ultima["id_operacao"]):
                op_saida = ClaudeTraderOrdemRule._op_por_id(ultima["id_operacao"])
                return ("encerrar_flat",
                        (op_saida or {}).get("tipo_posicao") or ultima.get("tipo_posicao"),
                        "Saída flat: cliente confirmou abertura e agora está sem posição (saída manual/SL nativo)",
                        op_saida or {"id_operacao": ultima.get("id_operacao")})
            # NAO confirmou abertura: so ESPERA se a op AINDA ESTA ABERTA (lag entre entregar o
            # 'abrir' e o EA executar). Se a op ja FECHOU sem ele confirmar, ele PERDEU aquela op
            # -> nao pode ficar travado esperando pra sempre; cai pro passo 2 e re-sincroniza na op
            # fresca atual. (Sem isso, uma conta que falha em abrir UMA op nunca mais opera.)
            op_ult = ClaudeTraderOrdemRule._op_por_id(ultima["id_operacao"])
            if op_ult and op_ult["status"] == "aberta":
                return (None, None, None, None)  # op ainda viva -> espera o EA abrir (lag)
            # op fechada e nunca confirmou -> nao trava; segue pro passo 2 (oferece op fresca)

        # 2) op fresca não-operada: reentrada primeiro, depois a principal (na janela de entrada)
        candidatas = []
        reentrada = ClaudeTraderOrdemRule._reentrada_aberta_hoje(id_estrategia)
        if reentrada:
            candidatas.append(reentrada)
        if principal and principal["status"] == "aberta":
            candidatas.append(principal)

        for cand in candidatas:
            ja = ClaudeTraderOrdemRule._ultima_entrega(account_number, id_estrategia, cand["id_operacao"])
            if ja:
                continue  # já operou/saiu dessa op → trava anti-perseguição (por id_operacao)
            if not ClaudeTraderOrdemRule._dentro_janela_entrada(cand):
                continue  # login atrasado NÃO persegue op em andamento
            return ("abrir", cand["tipo_posicao"], cand.get("motivo"), cand)

        return (None, None, None, None)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _conta_assina_estrategia(account_number, id_estrategia):
        sql = """SELECT 1
                 FROM metatrader_configs mc
                 INNER JOIN assinatura a ON a.id_usuario = mc.id_usuario
                 INNER JOIN plano_estrategia pe ON pe.id_plano = a.id_plano AND pe.id_estrategia = %s
                 WHERE mc.account_number = %s
                   AND mc.status = 'active'
                   AND (a.status = 'active' OR (a.status = 'trial' AND (a.trial_ends_at IS NULL OR a.trial_ends_at > NOW())))
                 LIMIT 1"""
        ret = GenericoModel().fetch(sql, [id_estrategia, account_number])
        return bool(ret)

    @staticmethod
    def _guia_hoje(id_estrategia):
        """A op PRINCIPAL de hoje (origem='principal'), independente do status. A reentrada
        é buscada à parte por _reentrada_aberta_hoje."""
        hoje = datetime.now(BRASILIA).strftime("%Y-%m-%d")
        r = (ClaudeTraderModel()
             .where(["id_ativos_base", "=", ID_ATIVOS_BASE])
             .where(["id_estrategia", "=", id_estrategia])
             .where(["modo", "=", "real"])
             .where(["origem", "=", "principal"])
             .where(["DATE(abertura_em)", "=", hoje])
             .order("id_operacao", "DESC").limit(1).find())
        return r[0] if r else None

    @staticmethod
    def _reentrada_aberta_hoje(id_estrategia):
        """A op de REENTRADA aberta de hoje (origem='reentrada'). No máx. 1 por vez (o cérebro
        garante). None quando o trilho de reentrada está OFF na estratégia (ex.: id=6/prod)."""
        hoje = datetime.now(BRASILIA).strftime("%Y-%m-%d")
        r = (ClaudeTraderModel()
             .where(["id_ativos_base", "=", ID_ATIVOS_BASE])
             .where(["id_estrategia", "=", id_estrategia])
             .where(["modo", "=", "real"])
             .where(["origem", "=", "reentrada"])
             .where(["status", "=", "aberta"])
             .where(["DATE(abertura_em)", "=", hoje])
             .order("id_operacao", "DESC").limit(1).find())
        return r[0] if r else None

    @staticmethod
    def _op_por_id(id_operacao):
        if not id_operacao:
            return None
        r = ClaudeTraderModel().where(["id_operacao", "=", id_operacao]).limit(1).find()
        return r[0] if r else None

    @staticmethod
    def _op_que_segue(account_number, id_estrategia, principal):
        """A op que o cliente está espelhando AGORA = a da última entrega viva (abrir/mover_stop).
        Pode ser a principal OU a reentrada. Fallback: a principal."""
        ultima = ClaudeTraderOrdemRule._ultima_geral(account_number, id_estrategia)
        if ultima and ultima["acao"] in ("abrir", "mover_stop", "manter") and ultima["id_operacao"]:
            op = ClaudeTraderOrdemRule._op_por_id(ultima["id_operacao"])
            if op:
                return op
        return principal

    @staticmethod
    def _dentro_janela_entrada(op):
        """True se a op abriu há <= JANELA_ENTRADA_MIN (login atrasado não persegue op em curso)."""
        ab = op.get("abertura_em")
        if not ab:
            return True
        if isinstance(ab, str):
            try:
                ab = datetime.strptime(ab[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return True
        agora = datetime.now(BRASILIA).replace(tzinfo=None)
        return (agora - ab) <= timedelta(minutes=JANELA_ENTRADA_MIN)

    @staticmethod
    def _ultima_entrega(account_number, id_estrategia, id_operacao):
        r = (ClaudeTraderMt5OrdensModel()
             .where(["account_number", "=", account_number])
             .where(["id_estrategia", "=", id_estrategia])
             .where(["id_operacao", "=", id_operacao])
             .order("id_ordem", "DESC").limit(1).find())
        return r[0] if r else None

    @staticmethod
    def _ultima_geral(account_number, id_estrategia):
        r = (ClaudeTraderMt5OrdensModel()
             .where(["account_number", "=", account_number])
             .where(["id_estrategia", "=", id_estrategia])
             .order("id_ordem", "DESC").limit(1).find())
        return r[0] if r else None

    @staticmethod
    def _confirmada(account_number, id_estrategia, id_operacao):
        """True se o EA JA reportou posicao aberta (tem_posicao_aberta_recebida=1) para esta op em
        algum poll — i.e., CONFIRMOU que abriu. So depois disso um 'flat' e considerado SAIDA real
        (encerrar_flat). Antes da confirmacao, flat = ainda nao abriu (lag) -> esperar. Cobre tanto
        o marcador 'manter' quanto qualquer 'mover_stop' (ambos gravados com tem_posicao=1)."""
        if not id_operacao:
            return False
        r = (ClaudeTraderMt5OrdensModel()
             .where(["account_number", "=", account_number])
             .where(["id_estrategia", "=", id_estrategia])
             .where(["id_operacao", "=", id_operacao])
             .where(["tem_posicao_aberta_recebida", "=", 1])
             .limit(1).find())
        return bool(r)

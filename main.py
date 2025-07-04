import discord
from discord.ext import commands
import os
import json
import asyncio
from discord.ui import View, Button

TOKEN = os.environ['DISCORD_TOKEN']
ARQUIVO = "campeonato.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variáveis principais
jogadores = {}
historico = []  # Ex: [{"jogo": 1, "posicoes": [...] }]

# Carregar dados do arquivo
if os.path.exists(ARQUIVO):
    with open(ARQUIVO, "r") as f:
        dados = json.load(f)
        jogadores = dados.get("jogadores", {})
        historico = dados.get("historico", [])


def salvar_dados():
    with open(ARQUIVO, "w") as f:
        json.dump({"jogadores": jogadores, "historico": historico}, f)


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")


@bot.command(name="start")
async def start(ctx, *nomes):
    global jogadores, historico
    if len(nomes) != 8:
        await ctx.send(
            "⚠️ Você deve passar exatamente 8 nomes para iniciar o campeonato.\n"
        )
        return
    jogadores = {nome: 0 for nome in nomes}
    historico = []
    salvar_dados()

    msg = """
    🧠 **Regras para o Campeonato de TFT:**

    👥 **8 jogadores** participam de **várias partidas!**
    🏅 A pontuação por colocação é:

    1º - 9 pontos
    2º - 7 pontos
    3º - 5 pontos
    4º - 3 pontos
    5º - 1 pontos
    6º - 0 pontos
    7º - -1 ponto
    8º - -2 pontos


    🎮 **Comandos úteis para o campeonato:**

    `!inserir`  
    → Registra uma partida via botões interativos.

    `!tabela`  
    → Mostra a pontuação atual.

    `!jogos`  
    → Mostra o resultado detalhado de cada partida.

    `!historico`  
    → Lista as partidas com nomes em ordem de colocação.

    `!fim`  
    → Encerra o campeonato e mostra o campeão.

    `!editar {numero}`
    → Edita a partida de número {numero}.

    ⚠️ Os nomes devem ser idênticos em todos os comandos.
    """

    await ctx.send("🏁 Campeonato iniciado com os jogadores:\n\n" +
                   ", ".join(jogadores.keys()) + "\n\n" + msg)


@bot.command(name="resultado")
async def resultado(ctx, *nomes):
    if not jogadores:
        await ctx.send(
            "❌ O campeonato ainda não foi iniciado. Use !start primeiro.")
        return
    if len(nomes) != 8:
        await ctx.send(
            "⚠️ Você precisa passar exatamente 8 nomes, ex: caio, disau, artu, ..., haimon"
        )
        return
    for nome in nomes:
        if nome not in jogadores:
            await ctx.send(f"❌ Jogador '{nome}' não faz parte do campeonato.")
            return

    pontos = [9, 7, 5, 3, 1, 0, -1, -2]
    jogo_num = len(historico) + 1
    msg = f"\n📦 **Partida {jogo_num} registrada:**\n"
    for i, nome in enumerate(nomes):
        jogadores[nome] += pontos[i]
        msg += f"{i+1}º - {nome} → {pontos[i]:+} (Total: {jogadores[nome]})\n"

    historico.append({"jogo": jogo_num, "posicoes": list(nomes)})
    salvar_dados()
    await ctx.send(msg)


class PosicaoButton(Button):

    def __init__(self, nome, autor_id):
        super().__init__(label=nome, style=discord.ButtonStyle.primary)
        self.autor_id = autor_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "❌ Apenas quem iniciou o comando pode interagir.",
                ephemeral=True)
            return

        if self.view is None:
            await interaction.response.send_message(
                "❌ Esta interação não é mais válida.", ephemeral=True)
            return

        self.view.escolhido = self.label
        self.view.usados.add(self.label)
        await interaction.response.defer()
        self.view.stop()


@bot.command(name="inserir")
async def inserir(ctx):
    if not jogadores:
        await ctx.send(
            "❌ O campeonato ainda não foi iniciado. Use !start primeiro.")
        return

    pos_texto = ["1º", "2º", "3º", "4º", "5º", "6º", "7º", "8º"]
    pontos = [9, 7, 5, 3, 1, 0, -1, -2]
    posicoes = []
    usados = set()
    autor_id = ctx.author.id
    comp_vencedora = "Não informada"

    class PosicaoButton(Button):

        def __init__(self, nome, autor_id):
            super().__init__(label=nome, style=discord.ButtonStyle.primary)
            self.autor_id = autor_id

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.autor_id:
                await interaction.response.send_message(
                    "❌ Apenas quem iniciou o comando pode interagir.",
                    ephemeral=True)
                return

            if self.view is None:
                await interaction.response.send_message(
                    "❌ Esta interação não é mais válida.", ephemeral=True)
                return

            self.view.escolhido = self.label
            self.view.usados.add(self.label)
            await interaction.response.defer()
            self.view.stop()

    class PosicaoView(View):

        def __init__(self, pos_label, usados_set):
            super().__init__(timeout=60)
            self.escolhido = None
            self.pos_label = pos_label
            self.usados = usados_set

            for nome in jogadores:
                if nome not in usados_set:
                    self.add_item(PosicaoButton(nome, autor_id))

        async def disable_all(self):
            for item in self.children:
                if isinstance(item, Button):
                    item.disabled = True

    await ctx.send("\n📥 Vamos registrar uma nova partida!\n\n")

    for i in range(8):
        pos_label = pos_texto[i]
        view = PosicaoView(pos_label, usados)
        msg = await ctx.send(
            f"➡️ Clique em quem ficou em **{pos_label} lugar**:", view=view)
        await view.wait()

        if not view.escolhido:
            await msg.edit(
                content=
                "⏰ Tempo esgotado ou nenhum jogador selecionado. Operação cancelada!",
                view=None)
            return

        posicoes.append(view.escolhido)
        usados.add(view.escolhido)
        await msg.edit(
            content=
            f"✅ **{view.escolhido}** registrado como {pos_label} lugar.",
            view=None)

        # Se for o primeiro lugar, perguntar a comp
        if i == 0:
            await ctx.send(
                f"🧪 digite no chat o nome da comp que **{view.escolhido}** usou nesta vitória:"
            )

            def check(m):
                return m.author.id == autor_id and m.channel == ctx.channel

            try:
                comp_msg = await bot.wait_for("message",
                                              timeout=30,
                                              check=check)
                comp_vencedora = comp_msg.content.strip()
            except asyncio.TimeoutError:
                comp_vencedora = "Não informada"
                await ctx.send(
                    "⏰ Tempo esgotado! A comp vencedora não foi registrada.")

    # Atualizar pontuação
    jogo_num = len(historico) + 1
    for i, nome in enumerate(posicoes):
        jogadores[nome] += pontos[i]

    # Salvar partida com comp do vencedor
    historico.append({
        "jogo": jogo_num,
        "posicoes": posicoes,
        "comp": comp_vencedora
    })
    salvar_dados()
    msg = f"📦 **Partida {jogo_num} registrada com sucesso!**\n"
    for i, nome in enumerate(posicoes):
        msg += f"{i+1}º - {nome} → {pontos[i]:+} (Total: {jogadores[nome]})\n"
    msg += f"\n🏆 Comp usada pelo vencedor ({posicoes[0]}): **{comp_vencedora}**"

    await ctx.send(msg)


@bot.command(name="tabela")
async def tabela(ctx):
    if not jogadores:
        await ctx.send("🚫 Nenhum campeonato iniciado ainda.")
        return

    ranking = sorted(jogadores.items(), key=lambda x: x[1], reverse=True)
    pos_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "🤮"]

    msg = "🏆 **Tabela de Pontuação Geral** 🏆\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"

    ultima_pontuacao = None
    posicao = 0
    repeticoes = 0

    for i, (nome, pts) in enumerate(ranking):
        if pts != ultima_pontuacao:
            posicao += 1 + repeticoes
            repeticoes = 0
        else:
            repeticoes += 1

        emoji = pos_emojis[posicao -
                           1] if posicao <= len(pos_emojis) else f"{posicao}º"

        msg += f"{emoji} {nome}: **{pts} pts**\n"
        ultima_pontuacao = pts

    msg += "━━━━━━━━━━━━━━━━━━━━━━━"
    await ctx.send(msg)


@bot.command(name="jogos")
async def jogos(ctx):
    if not historico:
        await ctx.send("❌ Nenhuma partida registrada ainda.")
        return

    msg = "📚 **Histórico de Partidas** 📚\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"

    pos_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "🤮"]

    for partida in historico:
        jogo_num = partida["jogo"]
        posicoes = partida["posicoes"]
        msg += f"🎮 **Jogo {jogo_num}**\n\n"
        for i, nome in enumerate(posicoes):
            emoji = pos_emojis[i] if i < len(pos_emojis) else f"{i+1}º"

            msg += f"{emoji} {nome}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"

    await ctx.send(msg)


@bot.command(name="comps")
async def comps(ctx):
    if not historico:
        await ctx.send("❌ Nenhuma partida registrada ainda.")
        return

    contagem = {}
    for partida in historico:
        comp = partida.get("comp", "Não informada")
        contagem[comp] = contagem.get(comp, 0) + 1

    msg = "🧪 **Composições Vencedoras:**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    for comp, qtd in sorted(contagem.items(), key=lambda x: x[1],
                            reverse=True):
        msg += f"🏆 {comp} — {qtd} vitória(s)\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━"
    await ctx.send(msg)


@bot.command(name="disau")
async def disau(ctx):
    await ctx.send("🌈 O Disau deve assumir sua bissexualidade!")


@bot.command(name="zenao")
async def zenes(ctx):
    await ctx.send("Máximo respito 🤝")


@bot.command(name="editar")
async def editar(ctx, numero: int):
    if not jogadores:
        await ctx.send("❌ O campeonato ainda não foi iniciado. Use !start primeiro.")
        return

    if numero < 1 or numero > len(historico):
        await ctx.send(f"⚠️ Número de jogo inválido. Use um número entre 1 e {len(historico)}.")
        return

        # Remover pontuação antiga
    pontos = [9, 7, 5, 3, 1, 0, -1, -2]
    jogo_antigo = historico[numero - 1]["posicoes"]
    for i, nome in enumerate(jogo_antigo):
        jogadores[nome] -= pontos[i]

    await ctx.send(f"✏️ Vamos editar os dados do **Jogo {numero}**.")

    pos_texto = ["1º", "2º", "3º", "4º", "5º", "6º", "7º", "8º"]
    posicoes = []
    usados = set()
    autor_id = ctx.author.id

    class PosicaoButton(Button):
        def __init__(self, nome, autor_id):
            super().__init__(label=nome, style=discord.ButtonStyle.primary)
            self.autor_id = autor_id

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.autor_id:
                await interaction.response.send_message(
                    "❌ Apenas quem iniciou o comando pode interagir.",
                    ephemeral=True
                )
                return

            if self.view is None:
                await interaction.response.send_message(
                    "❌ Esta interação não é mais válida.", ephemeral=True)
                return

            self.view.escolhido = self.label
            self.view.usados.add(self.label)
            await interaction.response.defer()
            self.view.stop()

    class PosicaoView(View):
        def __init__(self, pos_label, usados_set):
            super().__init__(timeout=60)
            self.escolhido = None
            self.pos_label = pos_label
            self.usados = usados_set

            for nome in jogadores:
                if nome not in usados_set:
                    self.add_item(PosicaoButton(nome, autor_id))

        async def disable_all(self):
            for item in self.children:
                if isinstance(item, Button):
                    item.disabled = True

    for i in range(8):
        pos_label = pos_texto[i]
        view = PosicaoView(pos_label, usados)
        msg = await ctx.send(
            f"➡️ Clique em quem ficou em **{pos_label} lugar**:", view=view)
        await view.wait()

        if not view.escolhido:
            await msg.edit(
                content="⏰ Tempo esgotado ou nenhum jogador selecionado. Operação cancelada.",
                view=None)
            return

        posicoes.append(view.escolhido)
        await msg.edit(
            content=f"✅ **{view.escolhido}** registrado como {pos_label} lugar.",
            view=None)

    # Atualizar pontuação nova
    for i, nome in enumerate(posicoes):
        jogadores[nome] += pontos[i]

    # Perguntar comp do 1º lugar
    primeiro = posicoes[0]
    await ctx.send(f"🧠 Qual foi a comp usada por **{primeiro}** no Jogo {numero}?")

    try:
        resposta = await bot.wait_for(
            "message",
            timeout=30.0,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        comp = resposta.content
    except asyncio.TimeoutError:
        comp = "Não informada"

    # Atualizar histórico com nova info
    historico[numero - 1] = {
        "jogo": numero,
        "posicoes": posicoes,
        "comp": comp
    }
    salvar_dados()

    # Mensagem final
    msg = f"✅ **Jogo {numero} editado com sucesso!**\n"
    for i, nome in enumerate(posicoes):
        msg += f"{i+1}º - {nome} → {pontos[i]:+} (Total: {jogadores[nome]})\n"
    msg += f"\n🏆 Composição do 1º lugar ({primeiro}): **{comp}**"

    await ctx.send(msg)



@bot.command(name="historico")
async def ver_historico(ctx):
    if not historico:
        await ctx.send("❌ Nenhuma partida registrada ainda.")
        return

    msg = "🕓 **Histórico de Partidas (Resumo):**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"

    for partida in historico:
        jogo_num = partida["jogo"]
        posicoes = partida["posicoes"]

        linha = " → ".join(posicoes)

        msg += f"🎮 **Jogo {jogo_num}:** {linha}\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━"
    await ctx.send(msg)


@bot.command(name="fim")
async def fim(ctx):
    if not jogadores:
        await ctx.send("❌ Nenhum campeonato em andamento.")
        return

    ranking = sorted(jogadores.items(), key=lambda x: x[1], reverse=True)
    vencedor, pontos_top = ranking[0]
    lanterna, pontos_bot = ranking[-1]

    pos_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "🤮"]

    msg = "🏁🏆 **CAMPEONATO FINALIZADO!** 🏆🏁\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📊 **CLASSIFICAÇÃO FINAL:**\n"

    for i, (nome, pts) in enumerate(ranking):
        emoji = pos_emojis[i] if i < len(pos_emojis) else f"{i+1}º"
        msg += f"{emoji} {nome}: **{pts} pts**\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"\n🎉 **GAPDOGAPDOGAP, {vencedor.upper()}!** 👑\nCagou na cabeça de geral com **{pontos_top} pontos**!\n"
    msg += f"\n🤢 **Vergonha alheia, imundiça, bizonho, esse é o(a) {lanterna.upper()}!** 🤮\nEssa CARNIÇA terminou com apenas **{pontos_bot} pontos**...\n MEU DEUS 😭\n"

    # 🔍 Análise das comps vencedoras
    comps_vencedoras = {}
    for partida in historico:
        comp = partida.get("comp", "Não informada")
        comps_vencedoras[comp] = comps_vencedoras.get(comp, 0) + 1

    if comps_vencedoras:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🧪 **Composições que mais venceram:**\n\n"
        for comp, qtd in sorted(comps_vencedoras.items(),
                                key=lambda x: x[1],
                                reverse=True):
            medalha = "🏆" if qtd > 1 else "🎯"
            msg += f"{medalha} **{comp}** — {qtd} vitória(s)\n"

    await ctx.send(msg)


@bot.command(name="reset")
async def reset(ctx):
    global jogadores, historico
    jogadores = {}
    historico = []
    salvar_dados()
    await ctx.send(
        "🔁 Campeonato resetado com sucesso. Use !start para começar de novo.")


@bot.command(name="ajuda")
async def ajuda(ctx):
    msg = """
🧠 **Como funciona o Campeonato de TFT:**

👥 **8 jogadores** participam de **várias partidas!**
🏅 A pontuação por colocação é:

1º - 9 pontos
2º - 7 pontos
3º - 5 pontos
4º - 3 pontos
5º - 1 pontos
6º - 0 pontos
7º - -1 ponto
8º - -2 pontos


🎮 **Comandos disponíveis:**

`!start jogador1 jogador2 ... jogador8`  
→ Inicia o campeonato com os 8 jogadores.

`!inserir`  
→ Registra uma partida via botões interativos.

`!tabela`  
→ Mostra a pontuação atual.

`!jogos`  
→ Mostra o resultado detalhado de cada partida.

`!historico`  
→ Lista as partidas com nomes em ordem de colocação.

`!fim`  
→ Encerra o campeonato e mostra o campeão.

`!reset`  
→ Limpa tudo manualmente.

`!editar {numero}`
→ Edita a partida de número {numero}.

`!ajuda`  
→ Mostra este menu.

⚠️ Os nomes devem ser idênticos em todos os comandos.
"""
    await ctx.send(msg)


bot.run(TOKEN)

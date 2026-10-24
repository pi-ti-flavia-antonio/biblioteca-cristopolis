// Pede confirmação antes de enviar um formulário marcado com data-confirmar.
// A pergunta aparece numa caixa com os botões "Sim" e "Não". Esc também cancela.
(function () {
    "use strict";

    var caixa = document.getElementById("caixa-confirmacao");
    if (!caixa) { return; }

    var titulo = document.getElementById("confirmacao-titulo");
    var detalhe = document.getElementById("confirmacao-detalhe");
    var botaoSim = document.getElementById("confirmacao-sim");
    var botaoNao = document.getElementById("confirmacao-nao");
    var pendente = null;

    function abrir(formulario, enviador) {
        pendente = { formulario: formulario, enviador: enviador };
        titulo.textContent = formulario.dataset.confirmar;
        detalhe.textContent = formulario.dataset.confirmarDetalhe || "";
        detalhe.hidden = !detalhe.textContent;
        var perigo = formulario.hasAttribute("data-confirmar-perigo");
        botaoSim.classList.toggle("button--danger", perigo);
        botaoSim.classList.toggle("button--primary", !perigo);
        caixa.showModal();
        (perigo ? botaoNao : botaoSim).focus();
    }

    function enviar(formulario, enviador) {
        formulario.dataset.confirmado = "1";
        if (formulario.requestSubmit) {
            formulario.requestSubmit(enviador || undefined);
        } else {
            formulario.submit();
        }
    }

    document.addEventListener("submit", function (evento) {
        var formulario = evento.target;
        if (!formulario.matches || !formulario.matches("form[data-confirmar]")) { return; }
        if (formulario.dataset.confirmado) {
            delete formulario.dataset.confirmado;
            return;
        }
        // Botões como "Buscar dados" não salvam nada, então não pedem confirmação.
        if (evento.submitter && evento.submitter.hasAttribute("data-sem-confirmacao")) { return; }

        evento.preventDefault();
        if (typeof caixa.showModal !== "function") {
            if (window.confirm(formulario.dataset.confirmar)) { enviar(formulario, evento.submitter); }
            return;
        }
        abrir(formulario, evento.submitter);
    });

    botaoSim.addEventListener("click", function () {
        var escolhido = pendente;
        pendente = null;
        caixa.close();
        if (escolhido) { enviar(escolhido.formulario, escolhido.enviador); }
    });
    // "Não" e a tecla Esc fecham a caixa sem enviar nada.
    botaoNao.addEventListener("click", function () {
        pendente = null;
        caixa.close();
    });
    caixa.addEventListener("cancel", function () {
        pendente = null;
    });
})();

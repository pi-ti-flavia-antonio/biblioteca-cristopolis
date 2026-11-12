// No cadastro de usuário, desliga o campo do número quando a carteirinha será gerada pelo sistema.
(function () {
    var opcoes = document.querySelectorAll('input[name="carteirinha_modo"]');
    var campo = document.getElementById("numero_carteirinha");
    if (!opcoes.length || !campo) { return; }

    function atualizar() {
        var automatico = document.querySelector('input[name="carteirinha_modo"]:checked').value === "automatico";
        campo.disabled = automatico;
        if (automatico) { campo.value = ""; }
    }

    opcoes.forEach(function (opcao) { opcao.addEventListener("change", atualizar); });
    atualizar();
})();

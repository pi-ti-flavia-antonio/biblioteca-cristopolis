(function () {
    "use strict";

    function marcarEmprestimosAtrasados() {
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);

        document.querySelectorAll("tr[data-due-date]").forEach((linha) => {
            const previsao = new Date(linha.dataset.dueDate);
            const badge = linha.querySelector(".badge");

            if (!badge) {
                return;
            }

            if (previsao < hoje) {
                badge.textContent = "Atrasado";
                badge.classList.add("badge--overdue");
            } else {
                badge.textContent = "Ativo";
                badge.classList.remove("badge--overdue");
            }
        });
    }

    marcarEmprestimosAtrasados();
})();

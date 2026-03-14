from abc import ABC, abstractmethod


class BaseChannel(ABC):
    """Classe base para todos os canais de notificação."""

    @abstractmethod
    def enviar(self, utilizador, assunto, corpo, dados=None):
        """Envia uma notificação pelo canal.

        Args:
            utilizador: instância de User
            assunto:    texto curto (ex: "Resultados de hoje")
            corpo:      texto completo da mensagem
            dados:      dict opcional com informação extra (ex: {'acertos': 3})
        """
        pass

    @abstractmethod
    def esta_configurado(self, utilizador):
        """Indica se o canal está configurado para este utilizador."""
        pass

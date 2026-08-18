import socket
import sys

def test_port(host, port):
    print(f"Tentando conexao de SAIDA (Outbound) para {host}:{port}...")
    try:
        # Tenta abrir um socket TCP puro na porta especificada com timeout de 5 segundos
        sock = socket.create_connection((host, port), timeout=5)
        print(f"[SUCESSO] Conexao TCP de saida estabelecida com {host}:{port}!")
        sock.close()
        return True
    except socket.timeout:
        print(f"[FALHA] Timeout: O firewall silenciou os pacotes de saida para {host}:{port}.")
        return False
    except Exception as e:
        print(f"[FALHA] Erro de rede: {e}")
        return False

if __name__ == "__main__":
    print("=== INICIANDO DIAGNOSTICO DE PORTAS SMTP DE SAIDA ===")
    
    gmail_host = "smtp.gmail.com"
    
    res_465 = test_port(gmail_host, 465)
    res_587 = test_port(gmail_host, 587)
    
    print("\n=== RESUMO DO DIAGNOSTICO ===")
    if not res_465 and not res_587:
        print("DIAGNOSTICO: O firewall da VPS esta BLOQUEANDO todo o trafego de saida (Outbound) para as portas 465 e 587.")
        print("Acao necessaria: Solicitar ao suporte ou ao Jair que libere as portas de SAIDA (outbound TCP) no firewall do servidor.")
    else:
        print("DIAGNOSTICO: A conexao de saida esta liberada. O problema pode ser nas credenciais ou configuracao do e-mail.")

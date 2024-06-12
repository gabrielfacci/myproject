import sys
import os
import subprocess

# Adiciona a pasta _internal ao sys.path
_internal_dir = os.path.join(os.path.dirname(__file__), '_internal')
if _internal_dir not in sys.path:
    sys.path.insert(0, _internal_dir)

# Lista de dependências
required_modules = ['requests', 'logging', 'mnemonic', 'colorama', 'ecdsa', 'hashlib', 'base58']

# Função para verificar e instalar dependências
def install_dependencies():
    # Certifica-se de que a pasta _internal existe
    if not os.path.exists(_internal_dir):
        os.makedirs(_internal_dir)

    # Verifica cada módulo e instala se necessário
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            print(f"Instalando {module}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", module, "--target", _internal_dir])

install_dependencies()

# Importação dos módulos necessários
import requests
import logging
import time
import itertools
import mnemonic
from colorama import Fore, Style, init
from ecdsa import SECP256k1, SigningKey
import hashlib
import base58
import random

init(autoreset=True)

retries = 3
email_autorizado = False

def clearNow():
    os.system("clear")

def titler(total_mnemonics_generated: int, btc_found: float, btc_to_usd: float):
    title = f"Insp: {total_mnemonics_generated} [Fnd {btc_found} BTC] = {btc_to_usd} $"
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()

def gerar_mnemônico():
    mnemo = mnemonic.Mnemonic("english")
    return mnemo.generate(strength=128)

def private_key_to_wif(private_key):
    extended_key = b'\x80' + private_key
    hashed_key = hashlib.sha256(extended_key).digest()
    double_hashed_key = hashlib.sha256(hashed_key).digest()
    checksum = double_hashed_key[:4]
    wif = base58.b58encode(extended_key + checksum)
    return wif

def public_key_to_address(public_key):
    sha256_bpk = hashlib.sha256(public_key).digest()
    ripemd160_bpk = hashlib.new('ripemd160', sha256_bpk).digest()
    extended_ripemd160_bpk = b'\x00' + ripemd160_bpk
    sha256_bpk2 = hashlib.sha256(extended_ripemd160_bpk).digest()
    sha256_bpk3 = hashlib.sha256(sha256_bpk2).digest()
    checksum = sha256_bpk3[:4]
    address = base58.b58encode(extended_ripemd160_bpk + checksum)
    return address.decode('utf-8')

def gerar_chave_privada():
    signing_key = SigningKey.generate(curve=SECP256k1)
    private_key = signing_key.to_string()
    verifying_key = signing_key.get_verifying_key()
    public_key = b'\x04' + verifying_key.to_string()
    return private_key, public_key

def verificar_saldo_BTC(address):
    for attempt in range(retries):
        try:
            response = requests.get(f"https://blockchain.info/balance?active={address}", timeout=10)
            response.raise_for_status()
            data = response.json()
            balance = data[address]["final_balance"]
            return balance / 100000000
        except requests.RequestException as e:
            if response.status_code == 429:
                delay = random.uniform(0.5, 2.0)  # Random delay to mitigate rate limit issues
                logging.info(f"\033[93mPerca de conexão, tentando reconectar. Esperando por {delay:.2f} segundos.\033[0m")
                time.sleep(delay)
            elif attempt < retries - 1:
                logging.info(f"\033[93mErro ao verificar o saldo, tentando novamente em {delay} segundos.\033[0m")
                time.sleep(delay)
            else:
                logging.info("\033[91mErro ao verificar o saldo.\033[0m")
    return 0

def recuperar_carteira_do_mnemônico(mnemonic_phrase):
    seed = mnemonic.Mnemonic.to_seed(mnemonic_phrase)
    private_key, public_key = gerar_chave_privada()
    address = public_key_to_address(public_key)
    balance = verificar_saldo_BTC(address)
    return mnemonic_phrase, balance, address

def obter_preco_btc():
    for attempt in range(3):
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data["bitcoin"]["usd"]
        except requests.RequestException as e:
            if response.status_code == 429:
                delay = random.uniform(0.5, 2.0)  # Random delay to mitigate rate limit issues
                logging.info(f"\033[93mPerca de conexão, tentando reconectar. Esperando por {delay:.2f} segundos.\033[0m")
                time.sleep(delay)
            else:
                logging.info(f"\033[93mErro ao obter o preço do BTC. Tentando novamente...\033[0m")
                time.sleep(5)
    return None

def iniciar_busca_carteiras():
    contador_mnemonic = 0
    total_btc_encontrado = 0

    # Inicia a busca por carteiras aleatórias automaticamente
    while True:
        mnemonic_phrase = gerar_mnemônico()
        mnemonic_phrase, balance, address = recuperar_carteira_do_mnemônico(mnemonic_phrase)
        preco_btc = obter_preco_btc()
        usd_value = balance * preco_btc if preco_btc else 0
        logging.info(f"\033[94mFrase Mnemônica: \033[93m{mnemonic_phrase}\033[0m")
        logging.info(f"\033[94mEndereço da Carteira: \033[93m{address}\033[0m")
        if balance > 0:
            logging.info(f"\033[94mSaldo: \033[93m{balance:.8f} BTC\033[0m (\033[93m${usd_value:.2f}\033[0m)")
            logging.info(f"\033[92mCarteira encontrada com saldo diferente de zero: {balance} BTC\033[0m")
            if preco_btc is not None:
                titler(contador_mnemonic, balance, usd_value)

                with open("found.txt", "a") as f:
                    f.write(f"Frase Mnemônica: {mnemonic_phrase}\n")
                    f.write(f"Endereço da Carteira: {address}\n")
                    f.write(f"Saldo: {balance} BTC (${usd_value:.2f})\n\n")
                resposta = input("Deseja continuar a busca? (sim/não): ")
                if resposta.lower() != 'sim':
                    break
            else:
                logging.info("\033[91mNão foi possível obter o preço do BTC. Tente novamente mais tarde.\033[0m")
        else:
            logging.info(f"\033[94mSaldo: \033[93m{balance:.8f} BTC\033[0m (\033[93m${usd_value:.2f}\033[0m)")

def open_link(url):
    try:
        subprocess.run(['termux-open-url', url])
    except Exception as e:
        print(f"Erro ao abrir o link: {e}")

def solicitar_email():
    print(Fore.GREEN + " __          __   _ _      _       ")
    print(Fore.GREEN + " \ \        / /  | | |    | |      ")
    print(Fore.GREEN + "  \ \  /\  / /_ _| | | ___| |_     ")
    print(Fore.GREEN + "   \ \/  \/ / _` | | |/ _ \ __|    ")
    print(Fore.GREEN + "    \  /\  / (_| | | |  __/ |_     ")
    print(Fore.GREEN + "   __\/_ \/ \__,_|_|_|\___|\__|    ")
    print(Fore.GREEN + "  / ____|                   | |    ")
    print(Fore.GREEN + " | (___   ___  __ _ _ __ ___| |__  ")
    print(Fore.GREEN + "  \___ \ / _ \/ _` | '__/ __| '_ \ ")
    print(Fore.GREEN + "  ____) |  __/ (_| | | | (__| | | |")
    print(Fore.GREEN + " |_____/ \___|\__,_|_|  \___|_| |_|")
    print(Fore.GREEN + "                                   ")
    print(Fore.GREEN + "                                   ")

    email = input("Digite seu email de compra: ")
    return email

def verificar_licenca(email, product_code):
    url = 'https://api.bluezinbet.com/verify_license.php'
    payload = {'email': email, 'product_code': product_code}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get('license_status') == 'active'
    except Exception as e:
        logging.error(f"Erro ao verificar a licença: {e}")
        return False

def show_menu():
    global retries  # Adiciona esta linha para permitir a alteração de retries
    global email_autorizado
    email = solicitar_email()

    if verificar_licenca(email, 'PPPB923M'):
        email_autorizado = verificar_licenca(email, 'PPPB924E')
    else:
        print("Sua assinatura não está ativa para o produto requerido.")
        sys.exit(0)

    try:
        clearNow()  # Limpa a tela do console

        print(Fore.GREEN + " __          __   _ _      _       ")
        print(Fore.GREEN + " \ \        / /  | | |    | |      ")
        print(Fore.GREEN + "  \ \  /\  / /_ _| | | ___| |_     ")
        print(Fore.GREEN + "   \ \/  \/ / _` | | |/ _ \ __|    ")
        print(Fore.GREEN + "    \  /\  / (_| | | |  __/ |_     ")
        print(Fore.GREEN + "   __\/_ \/ \__,_|_|_|\___|\__|    ")
        print(Fore.GREEN + "  / ____|                   | |    ")
        print(Fore.GREEN + " | (___   ___  __ _ _ __ ___| |__  ")
        print(Fore.GREEN + "  \___ \ / _ \/ _` | '__/ __| '_ \ ")
        print(Fore.GREEN + "  ____) |  __/ (_| | | | (__| | | |")
        print(Fore.GREEN + " |_____/ \___|\__,_|_|  \___|_| |_|")
        print(Fore.GREEN + "                                   ")
        print(Fore.GREEN + "                                   ")

        print("██ Minerador Cripto Mobile | V-1.5.3 ██\n")
        print("\033[1;37;40m🔥 MENU:\033[0;37;40m")
        print("\n1. 🚀 Iniciar Wallet Search")
        print("2. 💎 Mudar para versão PRO")
        print("3. ⚡ Acelerar mineração em 25x")
        print("4. 🌐 Comunidade")
        print("5. ❌ Sair")

        while True:
            option = input("\nEscolha uma opção: ")

            if option == "1":
                iniciar_busca_carteiras()
                input("\nPressione Enter para voltar ao menu principal...")
                clearNow()  # Limpa a tela do console

            elif option == "2":
                print('\033[1;33;40m \n🚀🔥 *** Versão PRÓ *** 🔥🚀')
                print("")
                print('\033[1;37;40m🔹 Minere até 150x mais rápido!')
                print('\033[1;37;40m🔹 Busque por mais de 30 criptomoedas diferentes!')
                print('\033[1;37;40m🔹 Grupo exclusivo de networking!')
                print('\033[1;37;40m🔹 Receba suporte prioritário 24/7!')
                print('\033[1;37;40m🔹 Orientações de Trading')
                print('\033[1;37;40m🔹 Acesso exclusivo a recursos premium!')
                print('\033[1;33;40m \n👉 Deseja adquirir a Versão PRÓ agora? (Sim/Não)')
                purchase_option = input("\033[1;33;40m Digite 'Sim' para comprar ou 'Não' para voltar ao menu: ")
                if purchase_option.lower() == 'sim':
                    print('\033[1;33;40m \n🛒 Você será redirecionado para a página de compra em 5 segundos...')
                    time.sleep(5)  # Aguarda 5 segundos
                    open_link('https://bit.ly/3VD1pjz')
                    input("\033[1;33;40m \nPressione Enter para voltar ao menu principal...")
                    clearNow()  # Limpa a tela do console
                    show_menu()  # Retorna ao menu principal
                elif purchase_option.lower() == 'não':
                    print('\nVoltando ao menu principal...')
                    time.sleep(2)  # Aguarda 2 segundos antes de voltar ao menu
                    clearNow()  # Limpa a tela do console
                    show_menu()  # Retorna ao menu principal
                else:
                    print('Opção inválida. Voltando ao menu principal...')
                    time.sleep(2)  # Aguarda 2 segundos antes de voltar ao menu
                    clearNow()  # Limpa a tela do console
                    show_menu()  # Retorna ao menu principal

            elif option == "3":
                if email_autorizado:
                    retries = 0
                    iniciar_busca_carteiras()
                    input("\nPressione Enter para voltar ao menu principal...")
                    show_menu()  # Retorna ao menu principal
                    clearNow()  # Limpa a tela do console
                else:
                    print(Fore.RED + "Você não tem permissão para acessar esta opção. Por favor, verifique sua licença.")
                    time.sleep(5)
                    open_link('https://go.perfectpay.com.br/PPU38CO7MT5')
                    time.sleep(5)
                    clearNow()
                    show_menu()  # Volta para o menu principal

            elif option == "4":
                print('Abrindo a comunidade...')
                open_link('https://t.me/+CEZdz4YNPQhkYjYx')
                input("\nPressione Enter para voltar ao menu principal...")
                show_menu()  # Retorna ao menu principal
                clearNow()  # Limpa a tela do console

            elif option == "5":
                print('Encerrando o programa...')
                time.sleep(2)  # Aguarda 2 segundos antes de encerrar o programa
                clearNow()  # Limpa a tela do console
                sys.exit()

            else:
                print("Opção inválida. Por favor, escolha uma opção válida.")

    except KeyboardInterrupt:
        print("\nEncerrando o programa...")
        time.sleep(2)  # Aguarda 2 segundos antes de encerrar o programa
        clearNow()  # Limpa a tela do console
        sys.exit()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    show_menu()

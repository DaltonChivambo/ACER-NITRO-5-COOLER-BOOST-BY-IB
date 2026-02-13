# Acer Nitro 5 Cooler Boost by IB

App desktop para controlar as ventoinhas do Acer Nitro 5 no Linux. Exibe RPM e permite controlar modo automático, Cooler Boost e velocidade manual.

## Modelos suportados

AN515-44, AN515-46, AN515-56, AN515-57, AN515-58

## Instalação rápida (recomendado)

Instala dependências (Python, tkinter, lm-sensors), configura o GRUB e instala o app:

```bash
sudo ./install-all.sh
```

Depois **reinicie** se o GRUB foi alterado. O app abre **sem pedir senha** (Polkit + sudoers). Execute pelo menu ou `sudo nitro-boost`.

### Desinstalar

Pelo app: **Opções → Desinstalar aplicativo**. Ou manualmente:

```bash
sudo ./uninstall.sh
```

## Instalação manual

### Pré-requisitos

1. **Pacotes:** `python3`, `python3-tk`, `lm-sensors`
2. **GRUB:** adicione `ec_sys.write_support=1` em GRUB_CMDLINE_LINUX_DEFAULT
3. **Reinicie** após alterar o GRUB

### Instalar o app

```bash
sudo ./install.sh
```

### Executar sem instalar

```bash
sudo ./nitro-boost
```

## Funcionalidades

- **RPM** — exibe CPU e GPU em RPM (EC ou estimado)
- **Automático** — ventoinhas controladas pela temperatura
- **Cooler Boost** — CPU e GPU individualmente
- **Manual** — slider 0–100% para cada ventoinha

## Licença

MIT

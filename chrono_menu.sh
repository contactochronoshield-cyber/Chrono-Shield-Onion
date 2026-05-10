#!/bin/bash
clear
AZUL='\e[1;34m'
VERDE='\e[1;32m'
ROJO='\e[1;31m'
NC='\e[0m'

# Banner Principal
figlet -f slant "CHRONO-SHELL"

echo -e "${AZUL}====================================================${NC}"
echo -e "${VERDE}  SISTEMA DE GESTIÓN - CHRONO SHIELD NETWORKS${NC}"
echo -e "${AZUL}====================================================${NC}"
echo -e "  CEO: ESTEBAN (DANI) | ESTADO: MODO PRUEBAS 5G"
echo -e "  UBICACIÓN: BARRANQUILLA, COLOMBIA"
echo -e "${AZUL}----------------------------------------------------${NC}"
echo -e "  [1] ESCANEAR RED (NMAP)"
echo -e "  [2] VERIFICAR SERVICIOS (ZETAS/CHRONO)"
echo -e "  [3] SALIR"
echo -e "${AZUL}----------------------------------------------------${NC}"
echo -n "  INGRESE COMANDO: "
read opcion

case $opcion in
  1) nmap -sn 192.168.1.0/24; read; ./chrono_menu.sh ;;
  2) ls ~/zetas; read; ./chrono_menu.sh ;;
  3) exit ;;
  *) ./chrono_menu.sh ;;
esac

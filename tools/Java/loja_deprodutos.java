package Loja_de_produtos;

import java.util.Scanner;
//import java.util.*;

public class Loja_de_produtos {

    static double[] precos;
    static String[] nomes;
    static int[] vendas;
    static Scanner entrada;
    static int index = 0;
    static int index_vendas = 0;

    static void menu_print(int a) {
        //Print do menu
        switch (a) {
            case 0:
//PRINT do Menu
                System.out.println("============== Menu de Opções ===================== ");
                System.out.println("1 – Cadastrar produto");
                System.out.println("2 – Listar produtos");
                System.out.println("3 – Vender produto");
                System.out.println("4 – Relatório de vendas");
                System.out.println("5 – Sair");
                System.out.println("----");
                System.out.println("== == == == == == == == == == == == == == == == ==");
                System.out.println("      Digite uma opção:   ");
                int menu_opcao = entrada.nextInt();
                if (menu_opcao < 1 || menu_opcao > 5) {
                    System.out.println("Digite um número entre 1 a 5");
                    menu_opcao = entrada.nextInt();
                }
                menu_print(menu_opcao);
                break;
            case 1:
//Cadastrar Produto
                if (index == 10) {
                    System.out.println("============================");
                    System.out.println("  Lista de Produtos cheia   ");
                    System.out.println("============================");

                } else {
                    System.out.println("============================");
                    System.out.println("Adicione um produto na lista");
                    System.out.println("============================");
                    System.out.println("Digite o nome do Produto:");
                    nomes[index] = entrada.nextLine();
                    while (nomes[index].equals("")) {
                        System.out.println("O nome não pode ser vazio, digite o nome do produto novamente:");
                        nomes[index] = entrada.nextLine();
                    }
                    if (nomes[index].equalsIgnoreCase("x")) {
                        return;
                    }
                    System.out.println("Digite o valor do Produto:");
                    precos[index] = entrada.nextDouble();
                    while (precos[index] <= 0) {
                        System.out.println("Valor não pode ser menor ou igual a zero");
                        System.out.println("Digite o valor do Produto:");
                        precos[index] = entrada.nextDouble();
                    }
                    System.out.println("+++++++++++++++++++++++++++++++");
                    System.out.println("Cadastro realizado com sucesso!");
                    System.out.println("+++++++++++++++++++++++++++++++");
                    index++;
                }
                // menu_print(0);
                break;
            case 2:
            case 3:
                //Listagem de Produtos

//Venda de Produtos
                if (index == 0) {
                    System.out.println("============================");
                    System.out.println("Há 0 produtos cadastrados, não há como fazer vendas.");
                    System.out.println("Por favor cadastre um produto.");
                    System.out.println("============================");
                    //  menu_print(0);
                    break;
                } else {
                    System.out.println("============================");
                    for (int i = 0; i < index; i++) {
                        System.out.println(i + 1 + " - " + nomes[i] + " | Preço: R$ " + precos[i]);
                    }
                    System.out.println(a == 2 ? "Listagem realizada com sucesso. " : " " + index + (index == 1 ? " produto cadastrado." : " produtos cadastrados."));
                    System.out.println("============================");
                    if (a == 2) {
                        //  menu_print(0);
                        break;
                    }

                }

                System.out.println("============================");
                System.out.println("Digite o codigo do produto que foi vendido");
                int indice_temp = entrada.nextInt() - 1;
                while (indice_temp < 0 || indice_temp > index - 1) {
                    System.out.println("O codigo não pode ser menor que 1 ou maior que 10, digite o codigo novamente");
                    indice_temp = entrada.nextInt() - 1;
                }
                vendas[index_vendas] = indice_temp;
                index_vendas++;
                System.out.println("+++++++++++++++++++++++++++++++");
                System.out.println("Venda realizada com sucesso!");
                System.out.println("+++++++++++++++++++++++++++++++");
                //     menu_print(0);
                break;
            case 4:
//Relatório de Vendas
                System.out.println("=== Relatório de Vendas ===");
                double soma = 0;
                if (index == 0) {
                    System.out.println("Não há produtos cadastrados, logo não há vendas.");
                    //     menu_print(0);
                    break;
                }
                if (index_vendas == 0) {
                    System.out.println("Não houve vendas");
                    //   menu_print(0);
                    break;
                }
                for (int i = 0; i < index; i++) {
                    double venda_atual = 0;
                    for (int j = 0; j < index_vendas; j++) {
                        venda_atual += i == vendas[j] ? 1 : 0;
                    }
                    System.out.println("===> CÓDIGO: " + (i + 1));
                    System.out.println("PRODUTO: " + nomes[i]);
                    System.out.println("Nº DE VENDAS: " + venda_atual);
                    System.out.println("PREÇO: R$ " + precos[i]);
                    System.out.println("TOTAL: R$ " + precos[i] * venda_atual);
                    soma += precos[i] * venda_atual;

                }
                System.out.println("=====================================");
                System.out.println("TOTAL GERAL DAS VENDAS: " + soma);
                System.out.println("=====================================");
                //    menu_print(0);
                break;
            case 5:
//Fechar
                System.out.println("=====================================");
                System.out.println("           FECHANDO                  ");
                System.out.println("=====================================");
                return;
        }
        System.out.print(a);
        if (a != 5 && a != 0) {
            menu_print(0);
        }
        //  menu_print(0);
    }

    public static void main(String[] args) {
        precos = new double[10];
        nomes = new String[10];
        vendas = new int[100];
        entrada = new Scanner(System.in);

        System.out.println("Tiago Campanário Braga              RA: 20029522");
        System.out.println("Gilmar da Silva Almeida Junior      RA: 21033057");
        System.out.println("Giovanni Ramos Alves                RA: 21027075");
        System.out.println("Nelson Aparecido Andre Junior       RA: 20684219 ");
        System.out.println("Ana Cristina Fasciana Mascelloni    RA: 21009380 ");
        menu_print(0);

    }
}

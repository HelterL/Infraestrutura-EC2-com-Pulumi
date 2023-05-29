# Infraestrutura-EC2-com-Pulumi
Criação de uma infraestrutura como código na cloud AWS utilizando a ferramenta pulumi na linguagem python.

## Infraestrura:
 * 1 - VPC
 * 4 - Subnets, sendo 2 públicas e 2 privadas
 * 1 - Internet Gateway
 * 2 - Tabelas de Roteamento
 * 1 - Grupo de segurança
 * 1 - Launch Template ou modelo de execução
 * 1 - Grupo de auto scaling
 * 1 - Target grupo apontado para o Grupo de auto scaling
 * 1 - Application Load Balancer
 * 1 - Listener Load Balancer
 * 1 - Scripts simples ao iniciar uma nova instância no grupo de auto scaling, informando na tela qual AZ a instância está

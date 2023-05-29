import pulumi
import pulumi_aws as aws
import base64

#Criação da VPC
vpc = aws.ec2.Vpc(
    "Vpc-ec2",
    cidr_block = "10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={ 
        "Name" : "VPC-EC2-Pulumi"
    }      
)

# Criação das Subnets, A e B são públicas, C e D Privadas
public_subnet_A = aws.ec2.Subnet(
    "Subnet-public-A", 
    cidr_block = "10.0.101.0/24",
    vpc_id=vpc.id,
    availability_zone='us-east-1a',
    tags = {
        "Name" : "Subnet-public-A"
    },
    map_public_ip_on_launch=True,  # Habilitar IPv4
)

public_subnet_B = aws.ec2.Subnet(
    "Subnet-public-B", 
    cidr_block = "10.0.102.0/24",
    vpc_id=vpc.id,
    availability_zone='us-east-1b', 
    tags = {
        "Name" : "Subnet-public-B"
    },
    map_public_ip_on_launch=True  # Habilitar IPv4 público ao inicializar instância
)

private_subnet_C = aws.ec2.Subnet(
    "Subnet-private-C", 
    cidr_block = "10.0.103.0/24",
    vpc_id=vpc.id,
    availability_zone='us-east-1a', 
    tags = {
        "Name" : "Subnet-private-C"
    },
    map_public_ip_on_launch=False 
)

private_subnet_D = aws.ec2.Subnet(
    "Subnet-private-D", 
    cidr_block = "10.0.104.0/24",
    vpc_id=vpc.id,
    availability_zone='us-east-1b', 
    tags = {
        "Name" : "Subnet-private-D"
    },
     map_public_ip_on_launch=False
)


#Criação do Internet Gateway, exemplificando ele faz a comunicação da internet externa para a internet interna da AWS.
internet_gateway = aws.ec2.InternetGateway(
    "Igw-ec2",
    vpc_id=vpc.id,
    tags = {
        "Name" : "IGW VPC"
    }
)

#Criação da tabela de roteamento pública
route_table_vpc_public = aws.ec2.RouteTable(
    "route-table-vpc-public",
    vpc_id=vpc.id,
    routes=[
        {
            "cidr_block" : "0.0.0.0/0",
            "gateway_id" : internet_gateway.id
        }
    ],
    tags = {
        "Name" : "Tabela de roteamento pública"
    }
)

#Criação da tabela de roteamento privada
route_table_vpc_private = aws.ec2.RouteTable(
    "route-table-vpc-private",
    vpc_id=vpc.id,
    tags = {
        "Name" : "Tabela de roteamento privada"
    }
)

# Associando as subnets públicas a tabela de roteamento pública
rt_table_assoc_public_1 = aws.ec2.RouteTableAssociation(
    "ec2-rta-public-1",
    route_table_id=route_table_vpc_public.id,
    subnet_id=public_subnet_A.id
)

rt_table_assoc_public_2 = aws.ec2.RouteTableAssociation(
    "ec2-rta-public-2",
    route_table_id=route_table_vpc_public.id,
    subnet_id=public_subnet_B.id
)

# Associando as subnets privadas a tabela de roteamento privada
rt_table_assoc_private_1 = aws.ec2.RouteTableAssociation(
    "ec2-rta-private-1",
    route_table_id=route_table_vpc_private.id,
    subnet_id=private_subnet_C.id
)

rt_table_assoc_private_2 = aws.ec2.RouteTableAssociation(
    "ec2-rta-private-2",
    route_table_id=route_table_vpc_private.id,
    subnet_id=private_subnet_D.id
)

# grupo de segurança, todo o trafégo está aberto somente para quem faz parte do grupo de segurança
sec_group = aws.ec2.SecurityGroup(
    "web-secgrp",
    description="Enable HTTP Access",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol='all',
            from_port=0,
            to_port=0,
            self=True
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol='tcp',
            from_port=22,
            to_port=22,
            cidr_blocks=['0.0.0.0/0'],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol='tcp',
            from_port=80,
            to_port=80,
            cidr_blocks=['0.0.0.0/0'],
        )
    ],
    egress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol='all',
            from_port=0,
            to_port=0,
            cidr_blocks=['0.0.0.0/0'],
        )
    ],
    vpc_id=vpc.id,
    tags = {
        "Name": "web-secgroup"
    }
)

#Script simples em bash, o launch template só ler em base64. logo se faz necessário converter o script para base64
script = """
        #!/bin/bash
        sudo su
        yum update -y
        yum install -y httpd
        systemctl start httpd
        systemctl enable httpd
        EC2AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
        echo '<center><h1> Esta EC2 esta na Zona: AZID </h1></center>' > /var/www/html/index.txt
        sed "s/AZID/$EC2AZ/" /var/www/html/index.txt > /var/www/html/index.html    
    """

# Converta o script Bash para base64
script_base64 = base64.b64encode(script.encode('utf-8')).decode('utf-8')
    
#criando template para subir instâncias no grupo de auto escalonamento
launch_template = aws.ec2.LaunchTemplate('example-launch-template',
    image_id='ami-053b0d53c279acc90', # Imagem ubuntu 22.04 lts 
    instance_type='t2.micro',
    key_name='suachavesemfinalpem',
    network_interfaces=[aws.ec2.LaunchTemplateNetworkInterfaceArgs(
        associate_public_ip_address=True,
        device_index=0,
        subnet_id=public_subnet_B.id,
        security_groups=[sec_group.id]
 )],
 user_data=script_base64
)

#criando grupo de auto scaling utilizando o templete criado anteriormente
autoscaling_group = aws.autoscaling.Group('example-autoscaling-group',
    launch_template={
        'id': launch_template.id,
        'version': '$Latest',
    },
    vpc_zone_identifiers=[public_subnet_A.id, public_subnet_B.id],
    desired_capacity=2,
    min_size=2,
    max_size=3,
    tags=[
        aws.autoscaling.GroupTagArgs(
            key='Name',
            value='example-auto-scaling-group',
            propagate_at_launch=True,
        )
    ]
)

# Crie um Application Load Balancer
load_balancer = aws.lb.LoadBalancer('example-load-balancer',
    load_balancer_type='application',
    subnets=[public_subnet_A,public_subnet_B],
    security_groups=[sec_group.id],
    tags={
        'Name': 'example-load-balancer',
    }
)

# Cria um target group para as instâncias do ALB
target_group = aws.lb.TargetGroup('example-target-group',
    port=80,
    protocol='HTTP',
    vpc_id=vpc.id,
    target_type='instance',
    tags={
        'Name': 'example-target-group',
    }
)

# Cria um listener para o ALB e associe ao target group
#ele irá receber as requisições de fora da internet na porta 80 e encaminhar para nosso ALB que está conectado com nosso target group
listener = aws.lb.Listener('example-listener',
    load_balancer_arn=load_balancer.arn,
    port=80,
    default_actions=[{
        'type': 'forward',
        'target_group_arn': target_group.arn,
    }],
    tags={
        'Name': 'example-listener',
    }
)

instance_main = aws.ec2.Instance(
    "Ansible-server",
    instance_type="t2.micro",
    key_name='suachavesemfinalpem',
    ami="ami-053b0d53c279acc90", #Ubuntu 22.04 lts
    tags={
        "Name": "Ansible-server",
    },
    subnet_id=public_subnet_B.id,
    vpc_security_group_ids=[sec_group.id],
    associate_public_ip_address=True,
    
)

pulumi.export("ip", instance_main.public_ip)
pulumi.export("hostname", instance_main.public_dns)
    

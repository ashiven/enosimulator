resource "hcloud_network" "vnet" {
  name     = "network"
  ip_range = "10.0.0.0/16"
}

resource "hcloud_network_subnet" "snet" {
  type         = "cloud"
  network_id   = hcloud_network.vnet.id
  network_zone = "eu-central"
  ip_range     = "10.0.2.0/24"
}

# creating a server auto-assigns a public ip
resource "hcloud_server" "server" {
  name        = "server"
  server_type = "cx11"
  image       = "ubuntu-20.04"
  location    = "nbg1"

  network {
    network_id = hcloud_network.vnet.id
  }

  depends_on = [
    hcloud_network_subnet.snet
  ]
}

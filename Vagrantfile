# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
#  config.vm.box = "ubuntu/xenial64"
  config.vm.box_check_update = false

  config.vm.define "ubuntu" do |instance|
    instance.vm.box = "ubuntu/xenial64"
  end

  config.vm.define "centos" do |instance|
    instance.vm.box = "centos7"
  end

  config.vm.define "sles" do |instance|
    instance.vm.box = "wandisco/sles-12.4-64"
  end

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
    #config.vm.provision :shell, path: "install.sh"
  end

  config.vm.provision "shell", inline: <<-SHELL
    cd /vagrant
    sudo ./install_mhVTL.sh
  SHELL
end

#!/bin/bash

arr=($(nmcli -g uuid c s --active))

for i in "${arr[@]}"
do
	#echo uuid=$i
	str=$(echo CONNECTION)
	str+=$'\n'
	str+=$(nmcli -g connection.id c s $i)
	str+=$'\n\n'
	str+=$(nmcli -m tabular -f ip4.address,ip4.gateway,ip4.domain c s $i)

	echo $str
	msgbox "$str"
done

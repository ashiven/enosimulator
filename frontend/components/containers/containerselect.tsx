"use client"

import ContainerChart from "@/components/containers/containerchart"
import { Button } from "@components/ui/button"
import {
   DropdownMenu,
   DropdownMenuContent,
   DropdownMenuLabel,
   DropdownMenuRadioGroup,
   DropdownMenuRadioItem,
   DropdownMenuSeparator,
   DropdownMenuTrigger,
} from "@components/ui/dropdown-menu"

import { useState } from "react"

export default function ContainerSelect({ containerList, containerData }: any) {
   const [selectedContainer, setSelectedContainer] = useState(containerList[0])

   return containerList.length > 0 && containerData ? (
      <div className="mt-8">
         <DropdownMenu>
            <DropdownMenuTrigger asChild>
               <Button variant="outline">Select Container</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
               <DropdownMenuLabel>Container Statistics</DropdownMenuLabel>
               <DropdownMenuSeparator />
               <DropdownMenuRadioGroup
                  value={selectedContainer}
                  onValueChange={setSelectedContainer}
               >
                  {containerList.map((containerName: string) => (
                     <DropdownMenuRadioItem
                        value={containerName}
                        key={containerName}
                     >
                        {containerName}
                     </DropdownMenuRadioItem>
                  ))}
               </DropdownMenuRadioGroup>
            </DropdownMenuContent>
         </DropdownMenu>
         <div>
            <ContainerChart data={containerData[selectedContainer]} />
         </div>
      </div>
   ) : (
      <div></div>
   )
}

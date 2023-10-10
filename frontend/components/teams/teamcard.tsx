import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
   HoverCard,
   HoverCardContent,
   HoverCardTrigger,
} from "@/components/ui/hover-card"
import {
   Popover,
   PopoverContent,
   PopoverTrigger,
} from "@/components/ui/popover"

interface TeamCardProps {
   TeamName: string
   TeamId: string
   TeamSubnet: string
   TeamAddress: string
   TeamExperience: string
}

export default function TeamCard(data: TeamCardProps) {
   return (
      <HoverCard>
         <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
               <CardTitle className="text-sm font-medium">
                  <HoverCardTrigger>{data.TeamName}</HoverCardTrigger>
               </CardTitle>
               <Popover>
                  <PopoverTrigger>
                     <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        strokeWidth="2"
                        stroke="#000000"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-4 w-4 text-muted-foreground"
                     >
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2" />
                        <path d="M9 3m0 2a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v0a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2z" />
                        <path d="M9 17v-5" />
                        <path d="M12 17v-1" />
                        <path d="M15 17v-3" />
                     </svg>
                  </PopoverTrigger>
                  <PopoverContent>
                     Exploiting: bla bla Patched: blub blub
                  </PopoverContent>
               </Popover>
            </CardHeader>
            <CardContent>
               <div className="text-2xl font-bold ">20000 Points</div>
               <div className="text-xs text-muted-foreground">
                  +200 since last round
               </div>
            </CardContent>
         </Card>
         <HoverCardContent>
            <span className="font-bold">Id: </span>
            <span>{data.TeamId}</span>
            <br />
            <span className="font-bold">Team Subnet: </span>
            <span>{data.TeamSubnet}</span>
            <br />
            <span className="font-bold">Address: </span>
            <span>{data.TeamAddress}</span>
            <br />
            <span className="font-bold">Experience Level: </span>
            <span>{data.TeamExperience}</span>
         </HoverCardContent>
      </HoverCard>
   )
}

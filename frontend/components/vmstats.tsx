import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
   Menubar,
   MenubarContent,
   MenubarItem,
   MenubarMenu,
} from "@/components/ui/menubar"
import { MyAreaGraph } from "@components/charts/areagraph"
import { MyBarChart } from "@components/charts/barchart"

/* Start sample data for bar charts and area charts */
import { useApiUrl, useCustom } from "@refinedev/core"
import dayjs from "dayjs"

interface Datum {
   date: string
   value: string
}
interface Chart {
   data: Datum[]
   total: number
   trend: number
}
const query = {
   start: dayjs().subtract(7, "days").startOf("day"),
   end: dayjs().startOf("day"),
}
/* End sample data for bar charts and area charts */

export default function VMStats() {
   /* Start sample data for bar charts and area charts */
   const API_URL = useApiUrl()

   const { data: dailyRevenue } = useCustom<Chart>({
      url: `${API_URL}/dailyRevenue`,
      method: "get",
      config: {
         query,
      },
   })

   const { data: dailyOrders } = useCustom<Chart>({
      url: `${API_URL}/dailyOrders`,
      method: "get",
      config: {
         query,
      },
   })

   const { data: newCustomers } = useCustom<Chart>({
      url: `${API_URL}/newCustomers`,
      method: "get",
      config: {
         query,
      },
   })
   /* End sample data for bar charts and area charts */

   return (
      <div className="container mx-auto mt-12">
         <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Revenue card */}
            <Card>
               <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                     Total Revenue
                  </CardTitle>
                  <svg
                     xmlns="http://www.w3.org/2000/svg"
                     viewBox="0 0 24 24"
                     fill="none"
                     stroke="currentColor"
                     strokeLinecap="round"
                     strokeLinejoin="round"
                     strokeWidth="2"
                     className="h-4 w-4 text-muted-foreground"
                  >
                     <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">$45,231.89</div>
                  <p className="text-xs text-muted-foreground">
                     +20.1% from last month
                  </p>
               </CardContent>
            </Card>
            {/* Revenue card */}
            <Card>
               <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                     Subscriptions
                  </CardTitle>
                  <svg
                     xmlns="http://www.w3.org/2000/svg"
                     viewBox="0 0 24 24"
                     fill="none"
                     stroke="currentColor"
                     strokeLinecap="round"
                     strokeLinejoin="round"
                     strokeWidth="2"
                     className="h-4 w-4 text-muted-foreground"
                  >
                     <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                     <circle cx="9" cy="7" r="4" />
                     <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">+2350</div>
                  <p className="text-xs text-muted-foreground">
                     +180.1% from last month
                  </p>
               </CardContent>
            </Card>
            {/* Subscriptions card */}
            <Card>
               <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Sales</CardTitle>
                  <svg
                     xmlns="http://www.w3.org/2000/svg"
                     viewBox="0 0 24 24"
                     fill="none"
                     stroke="currentColor"
                     strokeLinecap="round"
                     strokeLinejoin="round"
                     strokeWidth="2"
                     className="h-4 w-4 text-muted-foreground"
                  >
                     <rect width="20" height="14" x="2" y="5" rx="2" />
                     <path d="M2 10h20" />
                  </svg>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">+12,234</div>
                  <p className="text-xs text-muted-foreground">
                     +19% from last month
                  </p>
               </CardContent>
            </Card>
            {/* Sales card */}
            <Card>
               <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                     Active Now
                  </CardTitle>
                  <svg
                     xmlns="http://www.w3.org/2000/svg"
                     viewBox="0 0 24 24"
                     fill="none"
                     stroke="currentColor"
                     strokeLinecap="round"
                     strokeLinejoin="round"
                     strokeWidth="2"
                     className="h-4 w-4 text-muted-foreground"
                  >
                     <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                  </svg>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">+573</div>
                  <p className="text-xs text-muted-foreground">
                     +201 since last hour
                  </p>
               </CardContent>
            </Card>
         </div>
         {/* Some Charts with performance info */}
         <Card className="p-5">
            <Menubar>
               <MenubarMenu>
                  <MenubarContent aria-label="Options" className="gap-0">
                     {/* Revenue chart */}
                     <MenubarItem key="revenue" title="Revenue">
                        <Card>
                           <CardContent>
                              {/* TODO: - the data fields need to be filled with actual data */}
                              <MyAreaGraph
                                 data={dailyRevenue?.data?.data ?? []}
                                 stroke="#8884d8"
                                 fill="#cfeafc"
                              />
                           </CardContent>
                        </Card>
                     </MenubarItem>
                     {/* Orders chart */}
                     <MenubarItem key="orders" title="Orders">
                        <Card>
                           <CardContent>
                              <MyBarChart
                                 data={dailyOrders?.data?.data ?? []}
                                 fill="#ffce90"
                              />
                           </CardContent>
                        </Card>
                     </MenubarItem>
                     {/* Customers chart */}
                     <MenubarItem key="customers" title="Customers">
                        <Card>
                           <CardContent>
                              <MyAreaGraph
                                 data={newCustomers?.data?.data ?? []}
                                 stroke="#00bd56"
                                 fill="#ccf3f3"
                              />
                           </CardContent>
                        </Card>
                     </MenubarItem>
                  </MenubarContent>
               </MenubarMenu>
            </Menubar>
         </Card>
      </div>
   )
}

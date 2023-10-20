import React from "react"
import {
   Area,
   AreaChart,
   CartesianGrid,
   Legend,
   ResponsiveContainer,
   Tooltip,
   XAxis,
   YAxis,
} from "recharts"

const formatter = new Intl.DateTimeFormat("en-US", {
   month: "short",
   year: "numeric",
   day: "numeric",
})

interface Datum {
   date: string
   percentage: string
}

interface AreaGraphProps {
   data: Datum[]
   stroke: string
   fill: string
   name: string
}

export const MyAreaGraph: React.FC<AreaGraphProps> = ({
   data,
   stroke,
   fill,
   name,
}) => {
   const formatted = data.map(({ date, percentage }) => ({
      date: formatter.format(new Date(date)),
      percentage,
   }))

   return (
      <ResponsiveContainer aspect={3.5}>
         <AreaChart data={formatted}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis dataKey="percentage" />
            <Tooltip />
            <Legend />
            <Area
               name={name}
               type="monotone"
               dataKey="percentage"
               stroke={stroke}
               fill={fill}
            />
         </AreaChart>
      </ResponsiveContainer>
   )
}

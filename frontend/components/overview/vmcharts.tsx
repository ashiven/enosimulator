import VMSelect from "@/components/overview/vmchartselect"

const URL = process.env.API_URL || "http://127.0.0.1:5000"

async function getVmList() {
   try {
      const res = await fetch(`${URL}/vmlist`, {
         next: { revalidate: 0 },
      })
      const vmList = eval(await res.text())
      return vmList
   } catch (e) {
      return []
   }
}

async function getData(vmName: string) {
   try {
      const res = await fetch(`${URL}/vminfo?name=${vmName}`, {
         next: { revalidate: 0 },
      })
      const dataList = eval(await res.text())
      return dataList
   } catch (e) {
      return []
   }
}

function filterData(data: any) {
   const cpuData = data.map((item: any) => ({
      date: item.measuretime,
      percentage: item.cpuusage,
   }))
   const ramData = data.map((item: any) => ({
      date: item.measuretime,
      percentage: item.ramusage,
   }))
   const netData = data.map((item: any) => ({
      date: item.measuretime,
      rx: item.netrx,
      tx: item.nettx,
   }))

   return { cpuData, ramData, netData }
}

export default async function VMCharts() {
   const vmList = await getVmList()
   const vmData: any = {}

   await Promise.all(
      vmList.map(async (vmName: string) => {
         vmData[vmName] = filterData(await getData(vmName))
      })
   )

   return <VMSelect vmList={vmList} vmData={vmData} />
}

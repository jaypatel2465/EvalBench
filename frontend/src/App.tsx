import { useEffect, useMemo, useState } from 'react'
import { Chrome } from './components/Chrome'
import { Compare, JudgeReliability, Regressions } from './pages/Analysis'
import { Datasets, Models, SettingsPage } from './pages/Catalog'
import { Failures } from './pages/Failures'
import { Overview } from './pages/Overview'
import { Runs } from './pages/Runs'

function location(){const raw=window.location.hash.slice(1)||'/';const [path,query='']=raw.split('?');return{path,params:new URLSearchParams(query)}}
export default function App(){const[route,setRoute]=useState(location);useEffect(()=>{const update=()=>setRoute(location());window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[])
  const page=useMemo(()=>{const p=route.path;if(p==='/')return <Overview/>;if(p==='/runs')return <Runs/>;if(p.startsWith('/runs/'))return <Runs id={p.split('/')[2]}/>;if(p==='/failures')return <Failures params={route.params}/>;if(p==='/compare')return <Compare params={route.params}/>;if(p==='/regressions')return <Regressions/>;if(p==='/judge')return <JudgeReliability/>;if(p==='/datasets')return <Datasets/>;if(p==='/models')return <Models/>;if(p==='/settings')return <SettingsPage/>;return <Overview/>},[route])
  return <Chrome path={route.path}>{page}</Chrome>}

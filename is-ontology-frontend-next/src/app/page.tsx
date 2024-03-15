import Authentication, { Tokens } from '@/authentication'
import AppBar from '@mui/material/AppBar'
import Button from '@mui/material/Button'
import Box from '@mui/material/Box'
import Link from 'next/link'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import { useEffect, useState } from 'react'
import AuthProvider from '@/contexts/AuthContext'
import UserHeader from '@/components/UserHeader'
import { axios_instance } from '@/api'

export default function Home() {

  return <Box>
    <Typography variant='h1'>
      Центр Компетенций «Кибербезопасность» НТИ Энерджинет
    </Typography>
    <Typography>
      <b>Миссия ЦК ИБ:</b><br />Создать платформу и обеспечить развитие рынка цифровых знаний по ИБ.
    </Typography>
    <Typography>
      <b>Цели ЦК ИБ:</b><br />
      Выработать единый понятийный аппарат в сфере информационной и кибербезопасности. Сделать знания по ИБ оцифрованным и доступными для всех. Реализовывать проекты на базе открытой цифровой базы знаний по ИБ
    </Typography>
    <Typography>
      <b>Возможности применения открытой цифровой базы знаний ИБ:</b><br />
      Консолидация, корректировка и развитие государственной нормативной базы. Интерактивное взаимодействие государственных органов, образования, экспертов, бизнеса и т.д. Создание системы знаний и процессов ИБ в государстве, у предприятий и разработчиков продуктов. образовательных программ и научных работ в образовательной среде. Предоставление цифровой платформы и знаний для минимизации рисков и негативных последствий от киберинцидентов в ТЭК.
    </Typography>
  </Box>
}

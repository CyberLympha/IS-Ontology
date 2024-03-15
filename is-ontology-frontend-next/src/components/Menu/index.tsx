import Authentication from '@/authentication'
import { AuthContext } from '@/contexts/AuthContext'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import Link from 'next/link'
import React, { useContext } from 'react'

function Menu() {
    const userAuthorized = true// Authentication.authenticated
    return (
        <List component='nav' sx={{ width: '100%', bgcolor: 'background.paper' }} className='main-menu'>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/main'>Главная</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            <ListItem>
                <ListItemText>
                    <b>Законодательство</b>
                </ListItemText>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/fz'>Федеральные законы</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/pp'>Постановления правительства</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/fstek'>Приказы ФСТЭК</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            {userAuthorized && <><ListItem>
                <ListItemText><b>Словарь</b></ListItemText>
            </ListItem> <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <Link href='/terms'>Термины</Link>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <Link href='/triplets'>Триплеты</Link>
                        </ListItemText>
                    </ListItemButton>
                </ListItem></>}
            <ListItem>
                <ListItemText>
                    <b>Документы</b>
                </ListItemText>
            </ListItem>
            <ListItem>
                <ListItemText>
                    <b>Отчёты</b>
                </ListItemText>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/rep_2021_jul'>Отчёт за июль 2021 года</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/rep_2021_aug'>Отчёт за август 2021 года</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            {userAuthorized && <>
                <ListItem>
                    <ListItemText><b>Инструменты</b></ListItemText>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <a href='/clf/'>Классификатор статей</a>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <a href='/ie/'>Извлечение сущностей</a>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <a href='/terms_to_vote'>Голосование за сущности</a>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <a href='/ie/predicates'>Предикаты</a>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <a href='/ie/add'>Построение триплетов</a>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <a href='/triples_to_vote'>Голосование за триплеты</a>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
                <ListItem>
                    <ListItemButton>
                        <ListItemText>
                            <a href='/ie/graph'>Граф знаний</a>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
            </>}
            <ListItem>
                <ListItemText>
                    <b>Состав рабочей группы</b>
                </ListItemText>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/companies'>Компании участники</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/members'>Эксперты</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/exp_rate'>Рейтинг экспертов</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
            <ListItem>
                <ListItemButton>
                    <ListItemText>
                        <a href='/eng_rate'>Рейтинг инженеров</a>
                    </ListItemText>
                </ListItemButton>
            </ListItem>
        </List>
    )
}

export default Menu
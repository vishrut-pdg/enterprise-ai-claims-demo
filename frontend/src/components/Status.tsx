import { Badge } from './ui/badge'
export const humanize = (value: string) => value.replaceAll('_', ' ')
export function Status({value}: {value: string}) { return <Badge variant="secondary" className={`status status-${value}`}>{humanize(value)}</Badge> }
export const money = (amount: string, currency: string) => new Intl.NumberFormat('en-US', {style:'currency', currency}).format(Number(amount))

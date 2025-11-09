export interface RouterParams<T> {
  authorId?: string
  id?: string
  type?: number
  cardData?: T,
  formType?: string | undefined,
  longTakeTransitionParam?: Object | undefined
  surfaceUrl?: string
  isQueryCardData?:boolean
}

export interface TransitionParams {
  uIContext: UIContext
  componentId: string
}
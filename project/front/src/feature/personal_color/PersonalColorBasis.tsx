import type { PersonalColorDto } from '../../common/type'
import { useMessages } from '../../shared/i18n'
import { PERSONAL_COLOR_MESSAGES } from './messages'
import type { AxisName, FaceColorPart } from './messages'

const FACE_COLOR_PARTS: FaceColorPart[] = ['skin', 'lip', 'eye', 'eyebrow', 'hair']
const AXIS_NAMES: AxisName[] = ['warmth', 'depth', 'clarity']
// 축 막대가 끝까지 차는 점수. 그 이상은 끝에 붙인다
const AXIS_FULL_SCALE = 3

/** 가운데가 0. 부호 쪽으로 |값| / 3 만큼 채운다 (0~50%). */
export function axisFillPercent(value: number): number {
  return (Math.min(Math.abs(value), AXIS_FULL_SCALE) / AXIS_FULL_SCALE) * 50
}

function formatScore(value: number): string {
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}`
}

/** 결과 화면 하단 판정 근거: 얼굴 색 5개 → 3축 막대 → 피부 명도·대비 → 판정 문장. */
export function PersonalColorBasis({ personalColor }: { personalColor: PersonalColorDto }) {
  const messages = useMessages(PERSONAL_COLOR_MESSAGES)
  const { analysis, season, subtype } = personalColor
  const colorNameByPart: Partial<Record<FaceColorPart, string | null>> = {
    eye: analysis.faceColors.eyeColorName,
    hair: analysis.faceColors.hairColorName,
  }
  return (
    <section className="personal-color-basis" aria-labelledby="personal-color-basis-heading">
      <h3 id="personal-color-basis-heading" className="eyebrow">
        {messages.basisHeading}
      </h3>
      <p className="footnote">{messages.basisLede}</p>
      <ul aria-label={messages.faceColors} className="face-color-list">
        {FACE_COLOR_PARTS.map((part) => (
          <li key={part}>
            <span className="face-color-chip" style={{ background: analysis.faceColors[part] }} />
            <span className="face-color-name">{messages.faceColorNames[part]}</span>
            <span className="face-color-value">{colorNameByPart[part] ?? analysis.faceColors[part]}</span>
          </li>
        ))}
      </ul>
      <ul className="axis-list">
        {AXIS_NAMES.map((axisName) => {
          const value = analysis[axisName]
          const axis = messages.axes[axisName]
          const fillPercent = axisFillPercent(value)
          return (
            <li key={axisName} aria-label={`${axis.label} ${formatScore(value)}`}>
              <span className="axis-label">{axis.label}</span>
              <span className={`axis-end${value < 0 ? ' axis-end-active' : ''}`}>{axis.negative}</span>
              <span className="axis-track" aria-hidden="true">
                <span
                  className="axis-fill"
                  style={value < 0 ? { right: '50%', width: `${fillPercent}%` } : { left: '50%', width: `${fillPercent}%` }}
                />
              </span>
              <span className={`axis-end${value >= 0 ? ' axis-end-active' : ''}`}>{axis.positive}</span>
              <span className="axis-score">{formatScore(value)}</span>
            </li>
          )
        })}
      </ul>
      <dl className="basis-metrics">
        <div>
          <dt>{messages.skinLightness}</dt>
          <dd>{analysis.skinLightness.toFixed(1)}</dd>
        </div>
        <div>
          <dt>{messages.contrast}</dt>
          <dd>{analysis.contrast.toFixed(1)}</dd>
        </div>
      </dl>
      <p className="basis-verdict">{messages.verdict(analysis.warmth, analysis.depth, season, subtype)}</p>
    </section>
  )
}

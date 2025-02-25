import { Input } from "./ui/input";
import { Card, CardContent } from "./ui/card";
import { PositionSizingConfig, TimeframeConfig } from '../types/position-sizing';
import { useState } from 'react';

interface PositionSizingInputsProps {
  config: PositionSizingConfig;
  onChange: (config: PositionSizingConfig) => void;
}

interface ValidationErrors {
  [key: string]: {
    portfolioSize?: string;
    riskTolerancePercent?: string;
  };
}

export function PositionSizingInputs({ config, onChange }: PositionSizingInputsProps) {
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validate = (name: string, value: number) => {
    if (name.includes('portfolioSize')) {
      if (value <= 0) return 'Portfolio size must be greater than 0';
      if (value > 1000000000) return 'Portfolio size must be less than 1 billion';
    }
    if (name.includes('riskTolerancePercent')) {
      if (value <= 0) return 'Risk tolerance must be greater than 0';
      if (value > 100) return 'Risk tolerance must be less than 100%';
    }
    return undefined;
  };

  const handleChange = (timeframe: keyof PositionSizingConfig, field: keyof TimeframeConfig, value: number) => {
    const fieldName = `${timeframe}.${field}`;
    const error = validate(fieldName, value);
    
    setErrors(prev => ({
      ...prev,
      [timeframe]: {
        ...prev[timeframe],
        [field]: error
      }
    }));
    
    setTouched(prev => ({ ...prev, [fieldName]: true }));
    
    if (!error) {
      onChange({
        ...config,
        [timeframe]: {
          ...config[timeframe],
          [field]: value
        }
      });
    }
  };

  const renderTimeframeInputs = (
    timeframe: keyof PositionSizingConfig,
    title: string,
    description: string
  ) => {
    const timeframeConfig = config[timeframe];
    const timeframeErrors = errors[timeframe] || {};
    
    return (
      <div className="flex-1 p-4">
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
        <div className="space-y-2">
          <div>
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-gray-700 w-20">
                Portfolio:
              </label>
              <Input
                type="number"
                min="0"
                value={timeframeConfig.portfolioSize}
                onChange={(e) => handleChange(timeframe, 'portfolioSize', parseFloat(e.target.value) || 0)}
                onBlur={() => setTouched(prev => ({ ...prev, [`${timeframe}.portfolioSize`]: true }))}
                className={`h-8 text-sm ${touched[`${timeframe}.portfolioSize`] && timeframeErrors.portfolioSize ? 'border-red-500' : ''}`}
              />
            </div>
            {touched[`${timeframe}.portfolioSize`] && timeframeErrors.portfolioSize && (
              <p className="mt-1 text-xs text-red-500">{timeframeErrors.portfolioSize}</p>
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-gray-700 w-20">
                Risk (%):
              </label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={timeframeConfig.riskTolerancePercent}
                onChange={(e) => handleChange(timeframe, 'riskTolerancePercent', parseFloat(e.target.value) || 0)}
                onBlur={() => setTouched(prev => ({ ...prev, [`${timeframe}.riskTolerancePercent`]: true }))}
                className={`h-8 text-sm ${touched[`${timeframe}.riskTolerancePercent`] && timeframeErrors.riskTolerancePercent ? 'border-red-500' : ''}`}
              />
            </div>
            {touched[`${timeframe}.riskTolerancePercent`] && timeframeErrors.riskTolerancePercent && (
              <p className="mt-1 text-xs text-red-500">{timeframeErrors.riskTolerancePercent}</p>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <Card>
      <CardContent className="p-0">
        <div className="flex divide-x divide-gray-200">
          {renderTimeframeInputs(
            'dayTrading',
            'Day Trading',
            '1-5 Days'
          )}
          {renderTimeframeInputs(
            'swingTrading',
            'Swing Trading',
            '6-90 Days'
          )}
          {renderTimeframeInputs(
            'longTermInvesting',
            'Long Term Investing',
            '>90 Days'
          )}
        </div>
      </CardContent>
    </Card>
  );
} 
import React, { useState, useEffect } from 'react';
import client from '../../api/client';

const useColumnInternals = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get('/solve/reference/column-internals')
      .then((res) => {
      setData(res.data);
      setLoading(false);
      })
      .catch((err) => {
      console.error("Catalog connection error:", err);
      setLoading(false);
      });
  }, []);

  return { data, loading };
};

export default function ColumnInternalsPanel({ value, onChange, title = "Column Internals Specification" }) {
  const { data: catalog, loading } = useColumnInternals();
  const { internal_type, internal_key } = value;

  const handleTypeChange = (e) => {
    const nextType = e.target.value;
    let nextKey = "";
    
    if (catalog && catalog[nextType]) {
      const availableKeys = Object.keys(catalog[nextType]);
      if (availableKeys.length > 0) {
        nextKey = availableKeys[0];
      }
    }
    
    onChange({ ...value, internal_type: nextType, internal_key: nextKey });
  };

  const handleKeyChange = (e) => {
    onChange({ ...value, internal_key: e.target.value });
  };

  // Safe dictionary lookup using the catalog keys
  const meta = catalog && catalog[internal_type] ? catalog[internal_type][internal_key] : null;

  if (loading) {
    return <div className="p-4 text-slate-400 animate-pulse">Loading column internals registry...</div>;
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
        {title}
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Internal Hardware Classification</label>
          <select 
            value={internal_type} 
            onChange={handleTypeChange}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-slate-300 focus:outline-none focus:border-emerald-500 transition-colors"
          >
            <option value="random_packing">Random Packing</option>
            <option value="structured_packing">Structured Packing</option>
            <option value="tray">Tray Internals</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Hardware Device Catalog Profile</label>
          <select 
            value={internal_key} 
            onChange={handleKeyChange}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-slate-300 focus:outline-none focus:border-emerald-500 transition-colors"
          >
            {catalog && catalog[internal_type] && (
              Object.keys(catalog[internal_type]).map(key => {
                const item = catalog[internal_type][key];
                return (
                  <option key={key} value={key}>
                    {item.name || item.extended_name || key}
                  </option>
                );
              })
            )}
          </select>
        </div>
      </div>

      {/* Embedded Operational Specs Panel */}
      {meta ? (
        internal_type.includes("packing") ? (
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4">
            <div className="text-xs font-medium text-slate-500 uppercase mb-3 tracking-wider">Hydraulic Mass Transfer Rating Specs</div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-slate-500 text-xs">Typical HETP Target</div>
                <div className="text-slate-300 font-medium">{meta.typical_h_etp_m || meta.typical_HETP || '0.35'} m</div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">GPDC Fp Factor</div>
                <div className="text-slate-300 font-medium">{meta.packing_factor_sm1 || '65'} m⁻¹</div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Specific Surface Area</div>
                <div className="text-slate-300 font-medium">{meta.surface_area_m2_m3 || '250'} m²/m³</div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Operational ΔP/m Base</div>
                <div className="text-slate-300 font-medium">{meta.pressure_drop_Pa_per_m || '60'} Pa/m</div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Max Vapor Velocity Ceiling</div>
                <span className="inline-flex items-center px-2 py-0.5 mt-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {((meta.max_v_loading || 0.85) * 100).toFixed(0)}% Flood Limit
                </span>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Manufacturer Lineage</div>
                <div className="text-slate-400 text-xs italic">{meta.manufacturer || 'Generic Standard'}</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4">
            <div className="text-xs font-medium text-slate-500 uppercase mb-3 tracking-wider">Tray Layout Geometry Characteristics</div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-slate-500 text-xs">Typical Tray Efficiency</div>
                <div className="text-slate-300 font-medium">{((meta.typical_tray_efficiency || 0.70) * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Standard Spacing Layout</div>
                <div className="text-slate-300 font-medium">
                  {Array.isArray(meta.typical_tray_spacing_mm) ? meta.typical_tray_spacing_mm.join(' / ') : meta.tray_spacing_mm || '600'} mm
                </div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Turndown Operating Ratio</div>
                <span className="inline-flex items-center px-2 py-0.5 mt-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  {meta.turndown_ratio || meta.turn_down_ratio || '2.5'}:1 Range
                </span>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Est. Pressure Drop / Tray</div>
                <div className="text-slate-300 font-medium">{meta.pressure_drop_per_tray_mbar || '30'} mbar</div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Hole Diameter Profile</div>
                <div className="text-slate-300 font-medium">{meta.hole_diameter_mm ? `${meta.hole_diameter_mm} mm` : 'N/A (Valve / Bubble Cap)'}</div>
              </div>
              <div>
                <div className="text-slate-500 text-xs">Weep Point Limit</div>
                <div className="text-slate-400">{((meta.weep_point_fraction || 0.20) * 100).toFixed(0)}% Fraction</div>
              </div>
            </div>
          </div>
        )
      ) : (
        <div className="text-xs text-slate-500 italic p-2 border border-dashed border-slate-800 rounded text-center">
          Select an internal key to view design criteria
        </div>
      )}
    </div>
  );
}
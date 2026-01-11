"""
US-10: Store Geospatial Observation Data
"""
from flask import request, jsonify
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ObservationRecord(Base):
    """Database model for geospatial observation records."""
    __tablename__ = 'observations'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    timezone = Column(String(50), nullable=False)
    coordinates = Column(String(255), nullable=False)  # Simplified for compatibility
    satellite_id = Column(String(100), nullable=False)
    spectral_indices = Column(String(500))
    notes = Column(Text)
    
    def validate(self):
        """Validate required fields."""
        if not self.timezone or not self.coordinates or not self.satellite_id:
            raise ValueError('Missing required fields')

    def to_dict(self):
        """Convert object to dictionary for JSON responses."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'timezone': self.timezone,
            'coordinates': self.coordinates,
            'satellite_id': self.satellite_id,
            'spectral_indices': self.spectral_indices,
            'notes': self.notes
        }

def register(app, session):
    @app.route('/api/observations', methods=['POST'])
    def create_observation():
        try:
            data = request.get_json()
            
            # Handle timestamp
            ts_str = data.get('timestamp')
            ts_obj = datetime.fromisoformat(ts_str.replace('Z', '+00:00')) if ts_str else datetime.utcnow()

            observation = ObservationRecord(
                timestamp=ts_obj,
                timezone=data.get('timezone'),
                coordinates=data.get('coordinates'),
                satellite_id=data.get('satellite_id'),
                spectral_indices=data.get('spectral_indices'),
                notes=data.get('notes')
            )
            
            observation.validate()
            session.add(observation)
            session.commit()
            
            return jsonify({'id': observation.id, 'message': 'Observation created'}), 201
            
        except Exception as e:
            session.rollback()
            return jsonify({'error': str(e)}), 400

    @app.route('/api/observations/<int:obs_id>', methods=['GET'])
    def get_observation(obs_id):
        obs = session.query(ObservationRecord).filter_by(id=obs_id).first()
        if not obs:
            return jsonify({'error': 'Observation not found'}), 404
        return jsonify(obs.to_dict()), 200

    @app.route('/api/observations/<int:obs_id>', methods=['PUT'])
    def update_observation(obs_id):
        try:
            obs = session.query(ObservationRecord).filter_by(id=obs_id).first()
            if not obs:
                return jsonify({'error': 'Observation not found'}), 404
                
            data = request.get_json()
            
            # Update fields if provided
            obs.notes = data.get('notes', obs.notes)
            obs.spectral_indices = data.get('spectral_indices', obs.spectral_indices)
            obs.coordinates = data.get('coordinates', obs.coordinates)
            obs.timezone = data.get('timezone', obs.timezone)
            obs.satellite_id = data.get('satellite_id', obs.satellite_id)

            obs.validate()  # Ensure required fields still exist
            session.commit()
            
            return jsonify({'message': 'Observation updated successfully'}), 200
            
        except Exception as e:
            session.rollback()
            return jsonify({'error': str(e)}), 500

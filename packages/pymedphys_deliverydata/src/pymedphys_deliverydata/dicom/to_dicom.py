# Copyright (C) 2019 Cancer Care Associates and Simon Biggs

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version (the "AGPL-3.0+").

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License and the additional terms for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# ADDITIONAL TERMS are also included as allowed by Section 7 of the GNU
# Affero General Public License. These additional terms are Sections 1, 5,
# 6, 7, 8, and 9 from the Apache License, Version 2.0 (the "Apache-2.0")
# where all references to the definition "License" are instead defined to
# mean the AGPL-3.0+.

# You should have received a copy of the Apache-2.0 along with this
# program. If not, see <http://www.apache.org/licenses/LICENSE-2.0>.


from copy import deepcopy

import numpy as np

from pymedphys_base.deliverydata import DeliveryDataBase

from pymedphys_dicom.rtplan import (
    get_gantry_angles_from_dicom,
    build_control_points,
    replace_fraction_group,
    replace_beam_sequence,
    restore_trailing_zeros,
    merge_beam_sequences,
    get_fraction_group_index,
    get_beam_indices_of_fraction_group,
    convert_to_one_fraction_group,
    get_fraction_group_beam_sequence_and_meterset)

from ..utilities import (
    find_relevant_control_points,
    filter_out_irrelevant_control_points,
    get_all_masked_delivery_data,
    get_metersets_from_delivery_data)


def delivery_data_to_dicom(delivery_data: DeliveryDataBase,
                           dicom_template,
                           fraction_group_number=None):
    if fraction_group_number is None:
        pass

    single_fraction_group_template = convert_to_one_fraction_group(
        dicom_template, fraction_group_number)

    delivery_data = filter_out_irrelevant_control_points(delivery_data)
    template_gantry_angles = get_gantry_angles_from_dicom(
        single_fraction_group_template)

    gantry_tol = gantry_tol_from_gantry_angles(template_gantry_angles)

    all_masked_delivery_data = get_all_masked_delivery_data(
        delivery_data, template_gantry_angles, gantry_tol)

    fraction_group_index = get_fraction_group_index(
        single_fraction_group_template, fraction_group_number)

    single_beam_dicoms = []
    for beam_index, masked_delivery_data in enumerate(all_masked_delivery_data):
        single_beam_dicoms.append(delivery_data_to_dicom_single_beam(
            masked_delivery_data, single_fraction_group_template, beam_index,
            fraction_group_index))

    return merge_beam_sequences(single_beam_dicoms)


def determine_fraction_group_number(delivery_data, dicom_template,
                                    gantry_tol=None, meterset_tol=0.5):
    fraction_groups = dicom_template.FractionGroupSequence

    if len(fraction_groups) == 1:
        return fraction_groups[0].FractionGroupNumber

    fraction_group_numbers = [
        fraction_group.FractionGroupNumber
        for fraction_group in fraction_groups
    ]

    dicom_metersets_by_fraction_group = [
        get_fraction_group_beam_sequence_and_meterset(
            dicom_template, fraction_group_number)[1]
        for fraction_group_number in fraction_group_numbers
    ]

    split_by_fraction_group = [
        convert_to_one_fraction_group(dicom_template, fraction_group_number)
        for fraction_group_number in fraction_group_numbers
    ]

    gantry_angles_by_fraction_group = [
        get_gantry_angles_from_dicom(dataset)
        for dataset in split_by_fraction_group]

    gantry_tolerances = [
        gantry_tol_from_gantry_angles(gantry_angles)
        if gantry_tol is None
        else gantry_tol
        for gantry_angles in gantry_angles_by_fraction_group
    ]

    masked_delivery_data_by_fraction_group = []

    for gantry_angles, gantry_tol in zip(
        gantry_angles_by_fraction_group, gantry_tolerances
    ):
        try:
            masked = get_all_masked_delivery_data(
                delivery_data, gantry_angles, gantry_tol, quiet=True)
        except AssertionError:
            masked = DeliveryDataBase.empty()

        masked_delivery_data_by_fraction_group.append(masked)

    deliver_data_metersets_by_fraction_group = [
        get_metersets_from_delivery_data(masked_delivery_data)
        for masked_delivery_data in masked_delivery_data_by_fraction_group
    ]

    maximum_deviations = []
    for dicom_metersets, delivery_data_metersets in zip(
        dicom_metersets_by_fraction_group,
        deliver_data_metersets_by_fraction_group
    ):
        maximmum_diff = np.max(np.abs(
            np.array(dicom_metersets) - np.array(delivery_data_metersets)))

        maximum_deviations.append(maximmum_diff)

    deviations_within_tol = np.array(maximum_deviations) <= meterset_tol

    if np.sum(deviations_within_tol) < 1:
        raise ValueError(
            "A fraction group was not able to be found with the metersets "
            "and gantry angles defined by the tolerances provided. "
            "Please manually define the fraction group number.")

    if np.sum(deviations_within_tol) > 1:
        raise ValueError(
            "More than one fraction group was found that had metersets "
            "and gantry angles within the tolerances provided. "
            "Please manually define the fraction group number.")

    fraction_group_number = np.array(
        fraction_group_numbers)[deviations_within_tol]

    return fraction_group_number


def delivery_data_to_dicom_single_beam(delivery_data, dicom_template,
                                       beam_index, fraction_group_index):

    created_dicom = deepcopy(dicom_template)
    data_converted = coordinate_convert_delivery_data(delivery_data)

    beam = created_dicom.BeamSequence[beam_index]
    cp_sequence = beam.ControlPointSequence
    initial_cp = cp_sequence[0]
    subsequent_cp = cp_sequence[-1]

    all_control_points = build_control_points(
        initial_cp, subsequent_cp, data_converted)

    beam_meterset = '{0:.6f}'.format(data_converted['monitor_units'][-1])
    replace_fraction_group(
        created_dicom, beam_meterset, beam_index, fraction_group_index)
    replace_beam_sequence(created_dicom, all_control_points, beam_index)

    restore_trailing_zeros(created_dicom)

    return created_dicom


def coordinate_convert_delivery_data(delivery_data):
    monitor_units = delivery_data.monitor_units
    mlc = mlc_dd2dcm(delivery_data.mlc)
    jaw = jaw_dd2dcm(delivery_data.jaw)
    gantry_angle, gantry_movement = angle_dd2dcm(delivery_data.gantry)
    collimator_angle, collimator_movement = angle_dd2dcm(
        delivery_data.collimator)

    return {
        'monitor_units': monitor_units,
        'mlc': mlc,
        'jaw': jaw,
        'gantry_angle': gantry_angle,
        'gantry_movement': gantry_movement,
        'collimator_angle': collimator_angle,
        'collimator_movement': collimator_movement
    }


def jaw_dd2dcm(jaw):
    jaw = np.array(jaw, copy=True)
    jaw[:, 1] = -jaw[:, 1]

    converted_jaw = jaw.astype(str)
    converted_jaw[:, 1] = jaw.astype(str)[:, 0]
    converted_jaw[:, 0] = jaw.astype(str)[:, 1]
    converted_jaw = converted_jaw.tolist()

    return converted_jaw


def mlc_dd2dcm(mlc):
    mlc = np.array(mlc, copy=False)

    dicom_mlc_format = []
    for control_point in mlc:
        concatenated = np.hstack(
            [-control_point[-1::-1, 1], control_point[-1::-1, 0]])
        dicom_mlc_format.append(concatenated.astype(str).tolist())

    return dicom_mlc_format


def angle_dd2dcm(angle):
    diff = np.append(np.diff(angle), 0)
    movement = (np.empty_like(angle)).astype(str)

    movement[diff > 0] = 'CW'
    movement[diff < 0] = 'CC'
    movement[diff == 0] = 'NONE'

    converted_angle = np.array(angle, copy=False)
    converted_angle[converted_angle < 0] = (
        converted_angle[converted_angle < 0] + 360)

    converted_angle = converted_angle.astype(str).tolist()

    return converted_angle, movement


def gantry_tol_from_gantry_angles(gantry_angles):
    min_diff = np.min(np.diff(sorted(gantry_angles)))
    gantry_tol = np.min([min_diff / 2 - 0.1, 3])

    return gantry_tol
